(function (host) {
  'use strict';
  const compare = (a, b, op = 0) => [a === b, a !== b, a <= b, a < b, a >= b, a > b][op];
  class FusionGame {
    constructor(data, options = {}) {
      this.data = data;
      this.random = options.random || Math.random;
      this.audio = options.audio || { play() {}, stop() {}, volume() {} };
      this.storage = options.storage || {};
      this.onSave = options.onSave || (() => {});
      this.onFrame = options.onFrame || (() => {});
      this.hitTest = options.hitTest || null;
      this.overlapTest = options.overlapTest || null;
      this.global = new Map();
      this.images = new Map(data.images.map(i => [i.handle, i]));
      this.input = { x: -10000, y: -10000, click: false, held: new Set(), pressed: new Set() };
      this.trace = [];
      this.stopped = false;
      for (const def of Object.values(data.objects)) {
        if (def.flags & 4) this.global.set(def.handle, this.makeObject(def));
      }
      this.enter(0);
    }
    makeObject(def, instance = {}) {
      return { id: def.handle, def, x: instance.x || 0, y: instance.y || 0,
        layer: instance.layer || 0, visible: def.type <= 1 || !!(def.new_flags & 8),
        value: def.initial || 0, alt: [...(def.alterable_values || [])], flags: def.alterable_flags || 0,
        animation: 0, direction: 0, animationFrame: 0, animationProgress: 0,
        animationDone: false, cycles: 0, destroyed: false,
        pathProgress: 0, pathOriginX: instance.x || 0, pathOriginY: instance.y || 0,
        movementStopped: !def.movements?.[0]?.enabled || !def.movements[0].nodes?.length,
        opacity: def.ink === 1 ? Math.max(0, 1 - def.coefficient / 128) : 1,
        iniFile: 'freddy', iniGroup: 'freddy' };
    }
    enter(index) {
      if (!this.data.frames[index]) throw new Error(`Invalid frame ${index}`);
      this.frame = this.data.frames[index];
      this.objects = new Map();
      this.instances = [];
      this.time = 0;
      this.tickCount = 0;
      this.scrollX = 0;
      this.eventState = this.frame.events.map(() => ({ previous: false, once: false }));
      this.timerState = new Map();
      this.pendingFrame = null;
      for (const instance of this.frame.instances) {
        const def = this.data.objects[instance.object];
        if (!def || instance.parent) continue;
        const saved = this.global.get(def.handle);
        const obj = this.makeObject(def, instance);
        if (saved) {
          obj.value = saved.value; obj.alt = saved.alt; obj.flags = saved.flags;
          this.global.set(def.handle, obj);
        }
        Object.assign(obj, { x: instance.x, y: instance.y, layer: instance.layer, destroyed: false });
        if (!this.objects.has(def.handle)) this.objects.set(def.handle, []);
        this.objects.get(def.handle).push(obj);
        this.instances.push(obj);
      }
      this.onFrame(index);
    }
    list(id) {
      const current = this.objects.get(id);
      if (current) return current.filter(o => !o.destroyed);
      const global = this.global.get(id);
      return global ? [global] : [];
    }
    object(id) { return this.list(id)[0]; }
    value(id) { return this.object(id)?.value || 0; }
    counterImageHandle(obj) {
      const frames = obj.def.counter_frames || [];
      if (!frames.length) return undefined;
      const minimum = obj.def.minimum ?? 0, maximum = obj.def.maximum ?? minimum;
      const fraction = maximum > minimum ? (obj.value - minimum) / (maximum - minimum) : 0;
      const index = Math.floor(Math.max(0, Math.min(1, fraction)) * (frames.length - 1));
      return frames[index];
    }
    direction(obj) {
      const animations = obj.def.animations;
      if (!animations) return null;
      const anim = animations[obj.animation] || animations[0] || Object.values(animations)[0];
      return anim?.[obj.direction] || anim?.[0] || Object.values(anim || {})[0];
    }
    imageHandle(obj) {
      if (obj.def.type === 1) return obj.def.image;
      const dir = this.direction(obj);
      return dir?.frames[Math.min(obj.animationFrame, dir.frames.length - 1)];
    }
    bounds(obj) {
      const img = this.images.get(this.imageHandle(obj));
      const hotspot = img?.hotspot || [0, 0];
      return { x: obj.x - hotspot[0], y: obj.y - hotspot[1],
        width: img?.width || obj.def.width || 0, height: img?.height || obj.def.height || 0 };
    }
    overlap(a, b) {
      const x = this.bounds(a), y = this.bounds(b);
      const intersects = x.x < y.x + y.width && x.x + x.width > y.x && x.y < y.y + y.height && x.y + x.height > y.y;
      return intersects && (!this.overlapTest || this.overlapTest(a,b,x,y));
    }
    scrollOffset(obj) {
      if (obj.def.common_flags & 2048) return 0;
      return this.scrollX * (this.frame.layers?.[obj.layer]?.x_coefficient ?? 1);
    }
    pointerOver(obj) {
      if (obj.destroyed) return false;
      const bounds = this.bounds(obj);
      const x = this.input.x + this.scrollOffset(obj) - bounds.x;
      const y = this.input.y - bounds.y;
      if (x < 0 || y < 0 || x >= bounds.width || y >= bounds.height) return false;
      if (!(obj.def.new_flags & 4) && this.hitTest) return this.hitTest(this.imageHandle(obj), x, y);
      return true;
    }
    expression(parameter) {
      if (!parameter.tokens) return parameter.value ?? 0;
      const tokens = parameter.tokens;
      let cursor = 0;
      const precedence = { 2: 1, 4: 1, 6: 2, 8: 2 };
      const parse = (minimum = 0) => {
        let token = tokens[cursor++];
        if (!token) throw new Error('Missing expression operand');
        let left;
        if (token.type === -1) {
          if (token.number === 0 || token.number === 3) left = token.value;
          else if (token.number === -1 || token.number === 1) {
            left = parse();
            if (tokens[cursor]?.type !== -1 || tokens[cursor]?.number !== -2) throw new Error('Missing closing parenthesis');
            cursor++;
            if (token.number === 1) left = Math.floor(this.random() * Math.max(0, left));
          } else throw new Error(`Unknown system expression ${token.number}`);
        } else if (token.type > 0) {
          const obj = this.object(token.object);
          if (token.type === 33 && token.number === 82) {
            const item = parse();
            if (tokens[cursor]?.number !== -2) throw new Error('Missing INI closing parenthesis');
            cursor++;
            left = Number(this.storage[`${obj?.iniFile || 'freddy'}/${obj?.iniGroup || 'freddy'}/${item}`] || 0);
          } else if (token.type === 34) {
            const date = new Date();
            if (token.number === 85) left = date.getDate();
            else if (token.number === 86) left = date.getMonth() + 1;
            else throw new Error(`Unknown clock expression ${token.number}`);
          } else if (token.number === 80 && token.type === 7) left = obj?.value || 0;
          else if (token.number === 16) left = obj?.alt[token.value] || 0;
          else if (token.number === 11) left = obj?.x || 0;
          else throw new Error(`Unknown object expression ${token.type}:${token.number}`);
        } else throw new Error(`Unexpected expression ${token.type}:${token.number}`);
        while (cursor < tokens.length) {
          const operator = tokens[cursor];
          const priority = operator.type === 0 ? precedence[operator.number] : undefined;
          if (priority === undefined || priority < minimum) break;
          cursor++;
          const right = parse(priority + 1);
          if (operator.number === 2) left += right;
          if (operator.number === 4) left -= right;
          if (operator.number === 6) left *= right;
          if (operator.number === 8) left = right === 0 ? 0 : Math.trunc(left / right);
        }
        return left;
      };
      const result = parse();
      if (cursor !== tokens.length) throw new Error(`Expression has ${tokens.length - cursor} unread tokens`);
      return result;
    }
    condition(item, eventIndex, selections) {
      const { type, number, parameters: p } = item;
      const exp = index => this.expression(p[index]);
      const cmp = (value, index) => compare(value, exp(index), p[index].comparison);
      let result;
      if (type === -1) {
        if (number === -1 || number === -6 || number === -7) return true;
        if (number === -3) result = cmp(exp(0), 1);
      } else if (type === -3 && number === -1) result = this.tickCount === 0;
      else if (type === -4) {
        const delay = exp(0);
        if (number === -8) {
          const key = `${eventIndex}:${item.offset}`;
          const last = this.timerState.get(key) ?? 0;
          result = this.time + 0.001 >= last + delay;
          if (result) this.timerState.set(key, this.time);
        } else if (number === -7) result = this.time + 0.001 >= delay && this.time - this.stepMs < delay;
        else if (number === -1) result = this.time > delay;
      } else if (type === -6) {
        if (number === -1) result = this.input.pressed.has(exp(0));
        else if (number === -2) result = this.input.held.has(exp(0));
        else if (number === -5) result = this.input.click;
        else if (number === -4 || number === -7) {
          const id = p[number === -7 ? 1 : 0].object;
          const matches = this.list(id).filter(o => this.pointerOver(o));
          result = matches.length > 0 && (number !== -7 || this.input.click);
          if (result) selections.set(id, matches);
        }
      } else if (type >= 0) {
        const list = selections.get(item.object) || this.list(item.object);
        const matches = list.filter(obj => {
          if (type === 7 && number === -81) return cmp(obj.value, 0);
          if (number === -42 || number === -27) return cmp(obj.alt[exp(0)] || 0, 1);
          if (number === -4) return this.list(p[0].object).some(other => this.overlap(obj, other));
          if (number === -29) return obj.visible;
          if (number === -17) return cmp(obj.x, 0);
          if (number === -3) return obj.animation === exp(0) && !obj.animationDone;
          if (number === -2) return obj.animation === exp(0) && obj.animationDone;
          if (number === -1) return cmp(obj.animationFrame, 0);
          if (number === -7) return obj.movementStopped;
          throw new Error(`Unknown object condition ${type}:${number}`);
        });
        result = matches.length > 0;
        if (!(item.other_flags & 1) && result) selections.set(item.object, matches);
      }
      if (result === undefined) throw new Error(`Unknown condition ${type}:${number}`);
      return item.other_flags & 1 ? !result : result;
    }
    setPosition(obj, p) {
      const parent = p.parent === 65535 ? null : this.object(p.parent);
      obj.x = p.x + (parent?.x || 0);
      obj.y = p.y + (parent?.y || 0);
      if (p.flags & 2 && parent) {
        const image = this.images.get(this.imageHandle(parent));
        if (image) {
          obj.x += image.action_point[0] - image.hotspot[0];
          obj.y += image.action_point[1] - image.hotspot[1];
        }
      }
      if (p.parent === 65535) obj.layer = p.layer;
    }
    action(item, selections) {
      const { type, number, parameters: p } = item;
      const exp = index => this.expression(p[index]);
      if (type === -3) {
        if (number === 0) this.pendingFrame = this.frame.index + 1;
        else if (number === 2) this.pendingFrame = this.data.frame_handles[exp(0)];
        else if (number === 4) this.stopped = true;
        else if (number === 8) this.scrollX = Math.max(0, Math.min(this.frame.width - this.data.width, exp(0) - this.data.width / 2));
        else throw new Error(`Unknown storyboard action ${number}`);
        return;
      }
      if (type === -2) {
        if (number === 1) this.audio.stop();
        else if (number === 11) this.audio.play(p[0].handle, exp(1), 1);
        else if (number === 12) this.audio.play(p[0].handle, exp(1), exp(2));
        else if (number === 17) this.audio.volume(exp(0), exp(1));
        else throw new Error(`Unknown audio action ${number}`);
        return;
      }
      if (type === -5 && number === 0) {
        const def = this.data.objects[p[0].object];
        const obj = this.makeObject(def);
        const parent = this.object(p[0].parent);
        obj.layer = parent?.layer ?? p[0].layer;
        this.setPosition(obj, p[0]);
        if (!this.objects.has(obj.id)) this.objects.set(obj.id, []);
        this.objects.get(obj.id).push(obj);
        this.instances.push(obj);
        return;
      }
      const targets = selections.get(item.object) || this.list(item.object);
      for (const obj of targets) {
        if (type === 33) {
          if (number === 80) obj.iniGroup = exp(0);
          else if (number === 86) obj.iniFile = exp(0);
          else if (number === 87) {
            this.storage[`${obj.iniFile}/${obj.iniGroup}/${exp(0)}`] = exp(1);
            this.onSave(this.storage);
          } else throw new Error(`Unknown INI action ${number}`);
        } else if (type === 7 && number >= 80 && number <= 82) {
          const amount = exp(0);
          obj.value = number === 80 ? amount : obj.value + amount * (number === 81 ? 1 : -1);
          obj.value = Math.max(obj.def.minimum ?? -Infinity, Math.min(obj.def.maximum ?? Infinity, obj.value));
        } else if (number === 1) this.setPosition(obj, p[0]);
        else if (number === 2) obj.x = exp(0);
        else if (number === 17) {
          const animation = exp(0);
          if (obj.animation !== animation) Object.assign(obj, { animation, animationFrame: 0, animationProgress: 0, animationDone: false, cycles: 0 });
        } else if (number === 24) obj.destroyed = true;
        else if (number === 26) obj.visible = false;
        else if (number === 27) obj.visible = true;
        else if (number === 31) obj.alt[exp(0)] = exp(1);
        else if (number === 32) obj.alt[exp(0)] = (obj.alt[exp(0)] || 0) + exp(1);
        else if (number === 33) obj.alt[exp(0)] = (obj.alt[exp(0)] || 0) - exp(1);
        else if (number === 65) obj.opacity = Math.max(0, Math.min(1, 1 - exp(0) / 255));
        else throw new Error(`Unknown object action ${type}:${number}`);
      }
    }
    movePaths() {
      for (const obj of this.instances) {
        const path = obj.def.movements?.[0];
        if (obj.destroyed || obj.movementStopped || path?.type !== 5) continue;
        const node = path.nodes[0];
        // Clickteam advances 256 * speed << 5 in a 16-bit distance accumulator.
        const timer = this.frame.flags & 32768 ? this.frame.movement_timer_base / this.data.frame_rate : 1;
        obj.pathProgress += Math.trunc(256 * timer) * node.speed * 32;
        const distance = obj.pathProgress >>> 16;
        if (distance < node.length) {
          obj.x = obj.pathOriginX + Math.trunc(distance * node.cosine / 16384);
          obj.y = obj.pathOriginY + Math.trunc(distance * node.sine / 16384);
        } else {
          obj.x = obj.pathOriginX + node.dx;
          obj.y = obj.pathOriginY + node.dy;
          obj.pathProgress = 0;
          if (path.reposition) {
            obj.x = obj.pathOriginX; obj.y = obj.pathOriginY;
          }
          if (!path.loop) obj.movementStopped = true;
          else { obj.pathOriginX = obj.x; obj.pathOriginY = obj.y; }
        }
      }
    }
    animate() {
      for (const obj of this.instances) {
        if (obj.destroyed || obj.animationDone) continue;
        const dir = this.direction(obj);
        if (!dir || dir.frames.length <= 1) continue;
        obj.animationProgress += dir.maximum / 100;
        while (obj.animationProgress >= 1 && !obj.animationDone) {
          obj.animationProgress--;
          obj.animationFrame++;
          if (obj.animationFrame >= dir.frames.length) {
            obj.cycles++;
            if (dir.repeat > 0 && obj.cycles >= dir.repeat) {
              obj.animationFrame = dir.frames.length - 1;
              obj.animationDone = true;
            } else obj.animationFrame = dir.repeat_frame;
          }
        }
      }
    }
    step() {
      if (this.stopped) return;
      this.stepMs = 1000 / this.data.frame_rate;
      if (this.tickCount > 0) this.time += this.stepMs;
      this.movePaths();
      for (let i = 0; i < this.frame.events.length; i++) {
        const event = this.frame.events[i], state = this.eventState[i], selections = new Map();
        const conditions = event.conditions;
        let matched = true;
        for (const item of conditions) {
          if (!this.condition(item, i, selections)) { matched = false; break; }
        }
        const gated = conditions.some(c => c.type === -1 && c.number === -7);
        const once = conditions.some(c => c.type === -1 && c.number === -6);
        const run = matched && (!gated || !state.previous) && (!once || !state.once);
        state.previous = matched;
        if (!run) continue;
        state.once = true;
        for (const action of event.actions) this.action(action, selections);
        this.trace.push([this.frame.index, this.tickCount, i]);
        if (this.trace.length > 150) this.trace.shift();
        if (this.pendingFrame !== null) break;
      }
      this.input.click = false;
      this.input.pressed.clear();
      if (this.pendingFrame !== null) this.enter(this.pendingFrame);
      else { this.animate(); this.tickCount++; }
    }
  }
  if (typeof module !== 'undefined') module.exports = { FusionGame, compare };
  else host.FusionGame = FusionGame;
})(typeof window === 'undefined' ? globalThis : window);
