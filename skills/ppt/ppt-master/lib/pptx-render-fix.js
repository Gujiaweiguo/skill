/**
 * pptx-render-fix.js — Shared monkey-patch for pptxgenjs rendering issues
 *
 * Fixes:
 * 1. Text margins: OOXML defaults (0.1" L/R, 0.05" T/B) are too large,
 *    causing text boxes to silently shrink. Sets 2pt (25400 EMU) instead.
 * 2. \n line breaks: pptxgenjs v4 renders all lines at the same Y position.
 *    Splits multi-line text into separate addText calls with proper Y offsets.
 *
 * Usage in compile.js:
 *   var fix = require('./lib/pptx-render-fix');
 *   fix.patchPresentation(pres);
 */

function patchPresentation(pres) {
  var origAddSlide = pres.addSlide.bind(pres);

  pres.addSlide = function () {
    var slide = origAddSlide();
    var origAddText = slide.addText.bind(slide);

    slide.addText = function (text, opts) {
      if (!opts || typeof opts !== 'object') {
        return origAddText(text, opts);
      }

      // Fix 1: set small internal margins (2pt per side)
      opts.margin = [2, 2, 2, 2];

      // Fix 2: split \n into separate addText calls
      if (typeof text === 'string' && text.indexOf('\n') !== -1) {
        var lines = text.split('\n');
        if (lines.length <= 1) {
          return origAddText(text, opts);
        }

        var fontSize = opts.fontSize || 12;
        var lineSpacing = opts.lineSpacing || 1.2;
        var lineH = (fontSize / 72) * lineSpacing;
        if (lineH < 0.15) lineH = 0.2; // sane minimum
        var startY = opts.y || 0;

        for (var i = 0; i < lines.length; i++) {
          var line = lines[i];
          // Skip empty lines but maintain spacing
          if (line === '') continue;

          var lineOpts = {};
          for (var k in opts) {
            if (opts.hasOwnProperty(k)) {
              lineOpts[k] = opts[k];
            }
          }
          lineOpts.y = startY + i * lineH;
          lineOpts.h = lineH;
          lineOpts.valign = 'top'; // manual positioning

          origAddText(line, lineOpts);
        }
        return;
      }

      return origAddText(text, opts);
    };

    return slide;
  };

  return pres;
}

module.exports = { patchPresentation: patchPresentation };
