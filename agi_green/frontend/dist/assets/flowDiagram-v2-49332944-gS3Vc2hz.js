import { p as parser$1, f as flowDb } from "./flowDb-d35e309a-Ch8WP64l.js";
import { f as flowRendererV2, g as flowStyles } from "./styles-7383a064-DzmDgBj_.js";
import { t as setConfig } from "./index-BLy1h3wM.js";
import "./graph-BgFXEm22.js";
import "./layout-BDurn8sB.js";
import "./index-8fae9850-1AZqc4v7.js";
import "./clone-UKt3A5pd.js";
import "./edges-d417c7a0-Dq039-2Q.js";
import "./createText-423428c9-CHTAgR-R.js";
import "./line-DtzuX2Gi.js";
import "./array-DgktLKBx.js";
import "./path-Cp2qmpkd.js";
import "./channel-4QAhw09x.js";
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
//# sourceMappingURL=flowDiagram-v2-49332944-gS3Vc2hz.js.map
