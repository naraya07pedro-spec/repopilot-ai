import PublicDemo from "../../components/public-demo";
import bug from "../data/bug.json";
import feature from "../data/feature.json";
import failure from "../data/failure.json";
export default function Page(){return <PublicDemo records={[bug,feature,failure]}/>;}
