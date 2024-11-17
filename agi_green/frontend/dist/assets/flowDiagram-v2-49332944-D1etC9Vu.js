import { p as parser$1, f as flowDb } from "./flowDb-d35e309a-lWImPB8Y.js";
import { f as flowRendererV2, g as flowStyles } from "./styles-7383a064-xtM6p7sl.js";
import { t as setConfig } from "./index-TCZc8GNC.js";
import "./graph-COFI8eKA.js";
import "./layout-DmWx9SIm.js";
import "./index-8fae9850-Dkm1cn2_.js";
import "./clone-C9hMUx6Q.js";
import "./edges-d417c7a0-Cn7HwTF3.js";
import "./createText-423428c9-B4bjX2hF.js";
import "./line-BjdmiKVO.js";
import "./array-DgktLKBx.js";
import "./path-Cp2qmpkd.js";
import "./channel-BKfYN3Ui.js";
const diagram = {
  parser: parser$1,
  db: flowDb,
  renderer: flowRendererV2,
  styles: flowStyles,
  init: (cnf) => {
    if (!cnf.flowchart) {
      cnf.flowchart = {};
    }
    cnf.flowchart.arrowMarkerAbsolute = cnf.arrowMarkerAbsolute;
    setConfig({ flowchart: { arrowMarkerAbsolute: cnf.arrowMarkerAbsolute } });
    flowRendererV2.setConf(cnf.flowchart);
    flowDb.clear();
    flowDb.setGen("gen-2");
  }
};
export {
  diagram
};
//# sourceMappingURL=flowDiagram-v2-49332944-D1etC9Vu.js.map
