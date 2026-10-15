mergeInto(LibraryManager.library, {
  KingdomInstallAudioUnlock: function () {
    if (Module.kingdomUnlockAudio) return;
    Module.kingdomUnlockAudio = function (event) {
      if (!event.isTrusted || typeof WEBAudio === 'undefined' || !WEBAudio.audioContext) return;
      if (WEBAudio.audioContext.state === 'suspended')
        WEBAudio.audioContext.resume().catch(function (error) { console.warn('Audio activation failed:', error.name); });
      if (Module.kingdomAudioPaused) return;
      Object.keys(WEBAudio.audioInstances).forEach(function (id) {
        var source = WEBAudio.audioInstances[id].source;
        if (!source || !source.mediaElement || source.isStopped || source.pauseRequested || source.playPromise || source.playTimeout) return;
        var media = source.mediaElement;
        if (media.paused && !media.ended && source._startPlayback) source._startPlayback(media.currentTime || 0);
      });
    };
    ['keydown', 'pointerdown', 'touchstart'].forEach(function (name) {
      window.addEventListener(name, Module.kingdomUnlockAudio, true);
    });
    Module.deinitializers.push(function () {
      ['keydown', 'pointerdown', 'touchstart'].forEach(function (name) {
        window.removeEventListener(name, Module.kingdomUnlockAudio, true);
      });
    });
  },
  KingdomSetAudioPaused: function (paused) { Module.kingdomAudioPaused = !!paused; },
  KingdomBeginGameplayChecks: function () {
    Module.kingdomHammerAudio = { starts: 0, rms: 0, durations: [] };
    if (Module.kingdomAudioStartOriginal) return;
    var original = AudioBufferSourceNode.prototype.start;
    Module.kingdomAudioStartOriginal = original;
    AudioBufferSourceNode.prototype.start = function () {
      Module.kingdomHammerAudio.durations.push(this.buffer ? this.buffer.duration : -1);
      if (this.buffer && Math.abs(this.buffer.duration - 1.1538548752834468) < 0.02) {
        Module.kingdomHammerAudio.starts++;
        var values = this.buffer.getChannelData(0);
        var sum = 0;
        for (var i = 0; i < values.length; i++) sum += values[i] * values[i];
        Module.kingdomHammerAudio.rms = Math.sqrt(sum / values.length);
      }
      return original.apply(this, arguments);
    };
  },
  KingdomReportGameplayChecks: function (json) {
    var result = JSON.parse(UTF8ToString(json));
    result.hammerAudioStarts = Module.kingdomHammerAudio.starts;
    result.hammerAudioRms = Module.kingdomHammerAudio.rms;
    result.audioDurations = Module.kingdomHammerAudio.durations;
    result.audioEnabled = WEBAudio.audioWebEnabled;
    result.audioContextState = WEBAudio.audioContext ? WEBAudio.audioContext.state : 'absent';
    result.browser = navigator.userAgent;
    result.passed = result.passed && result.hammerAudioStarts > 0 && result.hammerAudioRms > 0.001 && result.audioContextState === 'running';
    var report = document.createElement('pre');
    report.id = 'gameplay-check-results';
    report.textContent = JSON.stringify(result, null, 2);
    document.body.appendChild(report);
    if (location.hostname === '127.0.0.1')
      fetch('/__tests__/result', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(result) }).catch(function () {});
  },
  KingdomSyncSave: function () {
    if (Module.kingdomSaveSyncing) {
      Module.kingdomSaveDirty = true;
      return;
    }
    var flush = function () {
      Module.kingdomSaveSyncing = true;
      FS.syncfs(false, function (error) {
        Module.kingdomSaveSyncing = false;
        if (error) {
          Module.kingdomExitPending = false;
          console.error('Kingdom save flush failed:', error);
          return;
        }
        if (Module.kingdomSaveDirty) {
          Module.kingdomSaveDirty = false;
          flush();
        } else if (Module.kingdomExitPending) {
          Module.kingdomExitPending = false;
          if (window.parent !== window) {
            window.parent.postMessage('kingdom-exit', location.origin);
          } else {
            location.reload();
          }
        }
      });
    };
    flush();
  },
  KingdomExitGame__deps: ['KingdomSyncSave'],
  KingdomExitGame: function () {
    Module.kingdomExitPending = true;
    _KingdomSyncSave();
  }
});
