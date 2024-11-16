import { p as parser$1, f as flowDb } from "./flowDb-d35e309a-CjAi9Gl0.js";
import { f as flowRendererV2, g as flowStyles } from "./styles-7383a064-DGeoERFX.js";
import { t as setConfig } from "./index-CFBt3vhw.js";
import "./graph-D9WLSh7X.js";
import "./layout-D16lSXlJ.js";
import "./index-8fae9850-DeRBkQRt.js";
import "./clone-nafVn6lD.js";
import "./edges-d417c7a0-Bzd-rv_-.js";
import "./createText-423428c9-CPV4ztI5.js";
import "./line-DEbD7Bn7.js";
import "./array-DgktLKBx.js";
import "./path-Cp2qmpkd.js";
import "./channel-DNA0pkNy.js";
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
//# sourceMappingURL=flowDiagram-v2-49332944-BQ478CN5.js.map
