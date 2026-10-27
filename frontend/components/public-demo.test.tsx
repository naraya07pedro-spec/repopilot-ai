import {render,screen,fireEvent,cleanup} from "@testing-library/react";
import {afterEach,expect,test,vi} from "vitest";
import PublicDemo from "./public-demo";
import bug from "../public-site/data/bug.json";
import feature from "../public-site/data/feature.json";
import failure from "../public-site/data/failure.json";
afterEach(cleanup);
test("public viewer never starts execution and identifies recordings",()=>{
 const fetchSpy=vi.spyOn(globalThis,"fetch");
 render(<PublicDemo records={[bug,feature,failure]}/>);
 expect(screen.getByRole("status").textContent).toContain("Recorded execution");
 expect(screen.queryByText("Approve fixture plan")).toBeNull();
 expect(fetchSpy).not.toHaveBeenCalled();fetchSpy.mockRestore();
});
test("renders actual diff, output and published PR; failure has no PR",()=>{
 render(<PublicDemo records={[bug,feature,failure]}/>);
 fireEvent.click(screen.getByRole("tab",{name:"Code diff"}));
 expect(screen.getByRole("tabpanel").textContent).toContain("+    return sum(values) / len(values)");
 fireEvent.click(screen.getByRole("tab",{name:"Tests"}));
 expect(screen.getByRole("tabpanel").textContent).toContain("3 passed");
 fireEvent.click(screen.getByRole("tab",{name:"Pull request"}));
 expect(screen.getByRole("link",{name:"Open real draft PR #2 ↗"}).getAttribute("href")).toMatch(/pull\/2$/);
 fireEvent.click(screen.getByRole("button",{name:/Rejected regression/}));
 fireEvent.click(screen.getByRole("tab",{name:"Pull request"}));
 expect(screen.getByText("No PR was prepared.")).toBeTruthy();
});
