'use strict';
class Panorama {
  constructor(config) {
    this.config = config;
    this.capture = document.createElement('canvas');
    this.capture.width = config.width; this.capture.height = config.height;
    this.captureContext = this.capture.getContext('2d', { alpha: false });
    this.surface = document.createElement('canvas');
    this.surface.width = config.width; this.surface.height = config.height;
    const gl = this.surface.getContext('webgl', { alpha: false, antialias: false, depth: false, stencil: false });
    this.gl = gl;
    if (!gl) return;
    const vertex = 'attribute vec2 position; varying vec2 uv; void main(){ gl_Position=vec4(position,0.0,1.0); uv=vec2(position.x*.5+.5,.5-position.y*.5); }';
    const fragment = `precision highp float; varying vec2 uv; uniform sampler2D scene;
      uniform vec2 size; uniform float zoom;
      void main(){
        float column=floor(uv.x*size.x);
        float angle=(column-floor(size.x/2.0))/(size.x/3.1415)+3.1415/2.0;
        float height=floor(max(1.0,size.y+sin(angle)*zoom-zoom));
        float top=floor(size.y/2.0)-floor(height/2.0);
        float row=(floor(uv.y*size.y)-top)/height;
        gl_FragColor=row<0.0||row>=1.0?vec4(0.0,0.0,0.0,1.0):texture2D(scene,vec2(uv.x,row));
      }`;
    const shader = (kind, source) => {
      const shader = gl.createShader(kind); gl.shaderSource(shader, source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      return shader;
    };
    const program = gl.createProgram();
    gl.attachShader(program, shader(gl.VERTEX_SHADER, vertex)); gl.attachShader(program, shader(gl.FRAGMENT_SHADER, fragment)); gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    gl.uniform2f(gl.getUniformLocation(program, 'size'), config.width, config.height);
    gl.uniform1f(gl.getUniformLocation(program, 'zoom'), config.zoom);
    this.texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, this.texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, config.resample ? gl.LINEAR : gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, config.resample ? gl.LINEAR : gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.viewport(0,0,config.width,config.height);
  }
  draw(context, canvas, x, y) {
    const { width, height, zoom } = this.config;
    const ctx = this.captureContext;
    ctx.fillStyle = '#000'; ctx.fillRect(0,0,width,height); ctx.drawImage(canvas,-x,-y);
    context.globalAlpha = 1; context.globalCompositeOperation = 'source-over';
    if (this.gl && !this.gl.isContextLost()) {
      this.gl.texImage2D(this.gl.TEXTURE_2D, 0, this.gl.RGB, this.gl.RGB, this.gl.UNSIGNED_BYTE, this.capture);
      this.gl.drawArrays(this.gl.TRIANGLES, 0, 6);
      context.drawImage(this.surface,x,y);
    } else {
      context.fillStyle = '#000'; context.fillRect(x,y,width,height);
      for (let i=0;i<width;i++) {
        const angle=(i-Math.floor(width/2))/(width/3.1415)+3.1415/2;
        const h=Math.floor(Math.max(1,height+Math.sin(angle)*zoom-zoom));
        context.drawImage(this.capture,i,0,1,height,x+i,y+Math.floor(height/2)-Math.floor(h/2),1,h);
      }
    }
  }
}
