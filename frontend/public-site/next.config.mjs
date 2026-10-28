import path from "node:path";
import {fileURLToPath} from "node:url";
export default {
 output:"export",
 trailingSlash:true,
 basePath:process.env.PUBLIC_BASE_PATH||"",
 poweredByHeader:false,
 turbopack:{root:path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..")},
};
