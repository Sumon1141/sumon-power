// injection.js — lightweight fingerprint spoofing (injected into proxied HTML)
(function(){
  try {
    var profile = window.__sp_profile || {};
    // override userAgent if provided
    if (profile.user_agent) {
      try {
        Object.defineProperty(navigator, 'userAgent', {get: function(){ return profile.user_agent; }});
      } catch(e) {}
    }

    // Canvas mitigation: add tiny noise
    var toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(){
      try{
        var ctx = this.getContext && this.getContext('2d');
        if (ctx){
          ctx.fillStyle = 'rgba(0,0,0,0.01)';
          ctx.fillRect(0,0,1,1);
        }
      }catch(e){}
      return toDataURL.apply(this, arguments);
    };

    // WebGL vendor/renderer spoof
    if (window.WebGLRenderingContext){
      var getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function(param){
        // 37445 = UNMASKED_VENDOR_WEBGL, 37446 = UNMASKED_RENDERER_WEBGL
        if (param === 37445) return profile.webgl_vendor || 'ARM';
        if (param === 37446) return profile.webgl_renderer || 'Mali';
        return getParameter.apply(this, arguments);
      };
    }

    // Battery API spoof
    if (navigator.getBattery){
      navigator.getBattery = function(){
        return Promise.resolve({
          charging: true,
          chargingTime: 0,
          dischargingTime: Infinity,
          level: 0.85
        });
      };
    }

    // Simple touch event randomization (if used on mobile)
    var origAddEvent = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(type, fn, opts){
      if (type === 'touchstart' || type === 'touchmove' || type === 'touchend'){
        var wrapped = function(e){
          try{
            // perturb touch coordinates slightly
            if (e.touches){
              for (var i=0;i<e.touches.length;i++){
                e.touches[i].clientX = e.touches[i].clientX + (Math.random()-0.5)*2;
                e.touches[i].clientY = e.touches[i].clientY + (Math.random()-0.5)*2;
              }
            }
          }catch(err){}
          return fn.apply(this, arguments);
        };
        return origAddEvent.call(this, type, wrapped, opts);
      }
      return origAddEvent.call(this, type, fn, opts);
    };

  }catch(e){console.error('injection error', e);} 
})();
