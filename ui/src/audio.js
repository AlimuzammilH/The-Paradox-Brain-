// All sound is synthesised in the browser: a low drone that opens up with tension, bell pings for claims,
// crackle for contradictions, a thump for the supernova. Muted until the listener turns it on.
export class Sound {
  constructor() { this.ctx = null; this.on = false; this.volume = 0.6; }

  _init() {
    if (this.ctx) return;
    const ctx = this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.master = ctx.createGain(); this.master.gain.value = 0;
    this.master.connect(ctx.destination);
    // reverb from a generated impulse: long, dark tail
    this.verb = ctx.createConvolver();
    const len = ctx.sampleRate * 4, ir = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = ir.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3.2);
    }
    this.verb.buffer = ir;
    const wet = ctx.createGain(); wet.gain.value = 0.55;
    this.verb.connect(wet).connect(this.master);
    // drone: detuned oscillators through a low-pass filter
    this.filter = ctx.createBiquadFilter(); this.filter.type = "lowpass"; this.filter.frequency.value = 260; this.filter.Q.value = 2;
    this.droneGain = ctx.createGain(); this.droneGain.gain.value = 0;
    this.filter.connect(this.droneGain); this.droneGain.connect(this.master); this.droneGain.connect(this.verb);
    for (const [f, type, g] of [[55, "sawtooth", 0.06], [55.4, "sawtooth", 0.06], [82.4, "triangle", 0.08], [110.2, "sine", 0.07], [164.8, "sine", 0.03]]) {
      const o = ctx.createOscillator(), og = ctx.createGain();
      o.type = type; o.frequency.value = f; og.gain.value = g;
      const lfo = ctx.createOscillator(), lg = ctx.createGain(); lfo.frequency.value = 0.05 + Math.random() * 0.1; lg.gain.value = 0.6;
      lfo.connect(lg).connect(o.detune); lfo.start();
      o.connect(og).connect(this.filter); o.start();
    }
    // air: filtered noise
    const nb = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), nd = nb.getChannelData(0);
    for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
    const ns = ctx.createBufferSource(); ns.buffer = nb; ns.loop = true;
    const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 900; bp.Q.value = 0.6;
    this.air = ctx.createGain(); this.air.gain.value = 0.012;
    ns.connect(bp).connect(this.air).connect(this.filter); ns.start();
    this.noise = nb;
    this.droneGain.gain.setTargetAtTime(1, ctx.currentTime, 2.5);
  }

  toggle() {
    this._init();
    this.on = !this.on;
    this.ctx.resume();
    this.master.gain.setTargetAtTime(this.on ? this.volume * 0.5 : 0, this.ctx.currentTime, 0.4);
    return this.on;
  }
  setVolume(v) {
    this.volume = v;
    if (this.ctx && this.on) this.master.gain.setTargetAtTime(v * 0.5, this.ctx.currentTime, 0.1);
  }
  get live() { return this.ctx && this.on; }

  tension(x) {   // 0..1: the drone opens and brightens
    if (!this.live) return;
    const t = this.ctx.currentTime;
    this.filter.frequency.setTargetAtTime(260 + x * 1400, t, 0.8);
    this.air.gain.setTargetAtTime(0.012 + x * 0.04, t, 0.8);
  }
  swell() {      // boot: the drone rises out of nothing
    if (!this.live) return;
    const t = this.ctx.currentTime;
    this.filter.frequency.cancelScheduledValues(t);
    this.filter.frequency.setValueAtTime(120, t);
    this.filter.frequency.exponentialRampToValueAtTime(900, t + 2.2);
    this.filter.frequency.exponentialRampToValueAtTime(260, t + 6);
  }
  ping(i = 0, side = "t") {
    if (!this.live) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const scale = side === "t" ? [659.3, 784, 987.8, 1174.7] : [622.3, 740, 932.3, 1108.7];
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = "sine"; o.frequency.value = scale[i % scale.length];
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.08, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.6);
    o.connect(g); g.connect(this.verb); g.connect(this.master); o.start(t); o.stop(t + 1.7);
  }
  crackle(strength = 1) {
    if (!this.live) return;
    const ctx = this.ctx, t = ctx.currentTime;
    for (let k = 0; k < 6; k++) {
      const s = ctx.createBufferSource(); s.buffer = this.noise;
      const hp = ctx.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 2500 + Math.random() * 3000;
      const g = ctx.createGain(), at = t + k * 0.05 + Math.random() * 0.04;
      g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(0.05 * strength, at + 0.003); g.gain.exponentialRampToValueAtTime(0.0001, at + 0.06);
      s.connect(hp).connect(g).connect(this.master); s.start(at, Math.random()); s.stop(at + 0.08);
    }
  }
  whoosh() {
    if (!this.live) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const s = ctx.createBufferSource(); s.buffer = this.noise;
    const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.Q.value = 3;
    bp.frequency.setValueAtTime(300, t); bp.frequency.exponentialRampToValueAtTime(3000, t + 0.35);
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.09, t + 0.12); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.5);
    s.connect(bp).connect(g); g.connect(this.master); g.connect(this.verb); s.start(t); s.stop(t + 0.6);
  }
  nova() {
    if (!this.live) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = "sine"; o.frequency.setValueAtTime(90, t); o.frequency.exponentialRampToValueAtTime(28, t + 1.2);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.7, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.8);
    o.connect(g); g.connect(this.master); g.connect(this.verb); o.start(t); o.stop(t + 2);
    const s = ctx.createBufferSource(); s.buffer = this.noise;
    const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.setValueAtTime(6000, t); lp.frequency.exponentialRampToValueAtTime(200, t + 2.5);
    const ng = ctx.createGain(); ng.gain.setValueAtTime(0.25, t); ng.gain.exponentialRampToValueAtTime(0.0001, t + 2.8);
    s.connect(lp).connect(ng); ng.connect(this.verb); ng.connect(this.master); s.start(t); s.stop(t + 3);
    // a bright chord rings out of the blast
    for (const f of [261.6, 392, 523.3, 659.3]) {
      const c = ctx.createOscillator(), cg = ctx.createGain(); c.type = "triangle"; c.frequency.value = f;
      cg.gain.setValueAtTime(0, t + 0.15); cg.gain.linearRampToValueAtTime(0.025, t + 0.5); cg.gain.exponentialRampToValueAtTime(0.0001, t + 5);
      c.connect(cg).connect(this.verb); c.start(t + 0.15); c.stop(t + 5.2);
    }
  }
  sting() {      // the objection hits
    if (!this.live) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const o = ctx.createOscillator(), g = ctx.createGain(), lp = ctx.createBiquadFilter();
    o.type = "sawtooth"; o.frequency.setValueAtTime(220, t); o.frequency.exponentialRampToValueAtTime(70, t + 0.7);
    lp.type = "lowpass"; lp.frequency.value = 900;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.12, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.9);
    o.connect(lp).connect(g); g.connect(this.master); g.connect(this.verb); o.start(t); o.stop(t + 1);
  }
}
