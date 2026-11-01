import ProductEntry from "../../components/product-entry";
import bug from "../data/bug.json";
import feature from "../data/feature.json";
import failure from "../data/failure.json";
import recording from "../data/local-agent.json";
export default function Page(){return <ProductEntry records={[bug,feature,failure]} recording={recording}/>;}
