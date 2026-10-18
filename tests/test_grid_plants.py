"""ericka-desk slice 6: the plant pages (E8 plant summary, E18 name matching, E29 plant status).

`/plants` carries each plant's status at the shell's "as of" time and `/plant/<code>` carries
the plant's trips, deratings, back-online notices, schedule lag, what to watch and next steps.
Both run `src/grid/asset.js` under the node harness (`tests/fixtures/grid/asset/render.mjs`)
against the synthetic records in `tests/fixtures/grid/plants/`.

What is proven here (intent §3 and §4 of docs/work/ericka-desk-2026-10-18):
- a notice that fits two plants is Unclear: listed with `.gn-unclear`, never linked to a plant
  and never counted for either;
- no technology or fuel word reaches the rendered output, and a name that reveals one is
  withheld;
- every view is filtered to the as-of time and redraws when the clock moves;
- the schedule lag reads "No data" when `outages.json` is absent or the value is missing.
Platform polish (2026-10-18) moved the markup onto the design system (one sortable sites table
with row links and a "More options" menu per row, the status in force as the page's anchor, a
filter bar kept in the address, and the plant's status and latest notice as the profile's
anchor). The pins below follow that markup and keep every invariant above; the new ones prove
the address filters and the table's row links.
What is not proven here: the look in a real browser.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "src" / "grid"
PLANTS = ROOT / "tests" / "fixtures" / "grid" / "plants"
NODE = shutil.which("node")
END = "2026-09-29T23:55"
EARLY = "2026-09-22T09:00"

# An independent list, kept apart from the page's own: the words that would reveal a
# technology or a fuel.
TECH = re.compile(r"\b(?:geothermal|thermal|solar|pv|hydro\w*|coal|diesel|bunker|fuel|oil|gas|"
                  r"lng|wind|biomass|battery|bess|nuclear|steam)\b", re.I)


@unittest.skipUnless(NODE, "the page script runs on node; this interpreter has none")
class PlantHarnessTests(unittest.TestCase):

    def report(self, *extra, bake=PLANTS):
        args = [NODE, "tests/fixtures/grid/asset/render.mjs", "--root", "."]
        if bake is not None:
            args += ["--bake", str(bake)]
        result = subprocess.run([*args, *extra], capture_output=True, text=True, cwd=ROOT,
                                timeout=300)
        try:
            report = json.loads(result.stdout)
        except ValueError:
            raise AssertionError("the harness printed no report: %s %s"
                                 % (result.stdout[-400:], result.stderr[-600:]))
        self.assertTrue(report.get("ok"), report.get("error"))
        self.assertEqual([], report["errors"])
        return report

    def collection(self, *extra):
        return self.report("--page", "assets", *extra)

    def profile(self, code, *extra, bake=PLANTS):
        return self.report("--page", "asset", "--code", code, *extra, bake=bake)

    # ---- E18: Unclear names are listed, not linked, not counted ----

    def test_a_notice_naming_two_plants_is_unclear_unlinked_and_listed(self):
        plants = self.collection("--at", END)["plants"]
        self.assertIn("gn-unclear", plants["unclear"])
        self.assertIn("SAMPLE and GEN units tripped", plants["unclear"])
        self.assertIn("04GEN, 08SAMPLE", plants["unclear"])
        self.assertNotIn("<a ", plants["unclear"])
        # Its time never stands as either plant's latest notice, in the feed or the table.
        self.assertNotIn("24 Sep 11:00", plants["list"])
        self.assertNotIn("24 Sep 11:00", plants["lists"])

    def test_an_unclear_notice_is_not_counted_for_either_plant(self):
        gen = self.profile("04GEN", "--at", END)["plants"]
        self.assertIn("<b class=\"mono\">2</b></dd></div>", gen["facts"].split("Deratings")[0])
        self.assertIn("V090000", gen["latest"])
        self.assertIn("gn-unclear", gen["unclear"])
        self.assertNotIn("<a ", gen["unclear"])
        sample = self.profile("08SAMPLE", "--at", END)["plants"]
        trips = sample["facts"].split("Deratings")[0]
        self.assertIn("<b class=\"mono\">0</b>", trips)
        self.assertIn("Derated", sample["status"])

    def test_a_low_confidence_outage_record_is_unclear(self):
        sample = self.profile("08SAMPLE", "--at", END)["plants"]
        self.assertIn("outage record: SAMPLE GEN", sample["unclear"])
        self.assertIn("No data", sample["facts"])

    # ---- intent §3: no technology or fuel ----

    def test_no_technology_or_fuel_word_is_rendered(self):
        views = [self.collection("--at", END)]
        views += [self.profile(code, "--at", END) for code in ("03LUZ", "04GEN", "08PEDC", "08SAMPLE")]
        for report in views:
            texts = list(report["plants"].values())
            if "collection" in report:
                texts += [report["collection"]["lists"], report["collection"]["tiles"]]
            else:
                p = report["profile"]
                texts += [p["name"]["html"], p["meta"]["html"], p["figures"], p["messages"],
                          p["events"], p["location"], p["register"]]
            for text in texts:
                found = TECH.findall(re.sub(r"<[^>]+>", " ", text or ""))
                self.assertEqual([], found, (report.get("code"), text[:300]))

    def test_a_name_that_reveals_the_technology_is_withheld(self):
        luz = self.profile("03LUZ", "--at", END)
        self.assertEqual("03LUZ", luz["profile"]["name"]["text"])
        self.assertIn("[…]", luz["plants"]["latest"])   # "Solar" and "fuel oil" redacted
        lists = self.collection("--at", END)["collection"]["lists"]
        self.assertNotIn("Synthetic Luzon Solar Farm", lists)
        self.assertNotIn("Sample Geothermal B", lists)

    # ---- the as-of clock ----

    def test_the_status_follows_the_as_of_time(self):
        report = self.collection("--at", END, "--then", EARLY)
        end, early = report["plants"], report["then"]
        self.assertIn("29 Sep 23:55", end["at"])
        self.assertIn("22 Sep 09:00", early["at"])
        self.assertIn("/plant/03LUZ", end["list"])
        self.assertNotIn("/plant/03LUZ", early["list"])       # its trip is on the 25th
        self.assertNotIn("/plant/08SAMPLE", early["list"])    # its deration is on the 23rd
        self.assertIn("22 Sep 08:00", early["list"])          # GEN's first trip
        self.assertNotIn("26 Sep", early["list"])
        self.assertEqual("", early["unclear"])                # the two-plant notice is the 24th

    def test_the_profile_counts_follow_the_as_of_time(self):
        report = self.profile("04GEN", "--at", END, "--then", EARLY)
        end, early = report["plants"], report["then"]
        self.assertIn("<b class=\"mono\">2</b>", end["facts"].split("Deratings")[0])
        self.assertIn("<b class=\"mono\">1</b>", early["facts"].split("Deratings")[0])
        self.assertIn("V080000", early["latest"])
        self.assertNotIn("V090000", early["latest"])
        self.assertNotIn("Back online", early["status"])

    def test_messages_and_events_after_the_as_of_time_are_hidden(self):
        early = self.profile("08PEDC", "--at", "2026-09-21T10:00")["plants"]
        self.assertNotIn("V133937", early["messages"])
        self.assertNotIn("/event/", early["events"])
        later = self.profile("08PEDC", "--at", END)["plants"]
        self.assertIn("V133937", later["messages"])

    # ---- the schedule lag ----

    def test_the_lag_is_read_from_the_outage_bake(self):
        pedc = self.profile("08PEDC", "--at", END)["plants"]
        self.assertIn("12 min", pedc["facts"])

    def test_the_lag_is_no_data_without_the_outage_bake_or_its_value(self):
        # The catalog bake carries no outages.json.
        bare = self.profile("08PEDC", bake=None)["plants"]
        self.assertIn("Schedule lag", bare["facts"])
        self.assertIn("No data", bare["facts"])
        self.assertIn("not in this build", bare["src"])
        # GEN's record states no lag_min.
        gen = self.profile("04GEN", "--at", END)["plants"]
        self.assertIn("No data", gen["facts"])

    # ---- links ----

    def test_each_plant_links_its_summary_event_and_journal(self):
        # Platform polish: each row of the one sites table links its plant (a row link and a
        # real link with the entity preview), and its "More options" menu holds the plant, its
        # events and its journal entries.
        lists = self.collection("--at", END)["plants"]["lists"]
        self.assertIn('<tr data-href="/plant/08PEDC">', lists)
        self.assertIn('href="/plant/08PEDC" data-entity="plant:08PEDC"', lists)
        self.assertIn('href="/event/sample-event-2026-09-21"', lists)
        self.assertIn('href="/journal?plant=08PEDC"', lists)
        self.assertIn('aria-label="More options for 08PEDC"', lists)
        self.assertIn('class="gn-menu" role="menu" hidden', lists)
        pedc = self.profile("08PEDC", "--at", END)["plants"]
        self.assertIn('href="/journal?plant=08PEDC"', pedc["next"])

    def test_only_plants_with_a_notice_filter(self):
        report = self.collection("--at", END, "--only")
        self.assertNotIn("/plant/08PLACE", report["plants"]["lists"])
        self.assertIn("/plant/04GEN", report["plants"]["lists"])
        self.assertEqual("true", report["plants"]["only"])

    # ---- platform polish: the address filters, the status badges and the anchor ----

    def test_the_address_filters_the_one_sites_table(self):
        everything = self.collection("--at", END)["plants"]
        self.assertEqual("5 sites", everything["found"])
        self.assertEqual(1, everything["lists"].count('id="sites-table"'))
        self.assertIn("data-sortable", everything["lists"])
        visayas = self.collection("--at", END, "--qs", "grid=CVIS")["plants"]
        self.assertEqual("4 of 5 sites", visayas["found"])
        self.assertNotIn("/plant/03LUZ", visayas["lists"])
        tripped = self.collection("--at", END, "--qs", "status=trip")["plants"]
        rows = re.findall(r'<tr data-href="/plant/([^"]+)"', tripped["lists"])
        self.assertEqual({"04GEN", "03LUZ"}, set(rows))
        self.assertEqual("2 of 5 sites", tripped["found"])
        nothing = self.collection("--at", END, "--qs", "grid=CMIN")["plants"]
        self.assertIn("gn-empty", nothing["lists"])
        self.assertIn("Clear filters", nothing["lists"])

    def test_the_status_in_force_is_counted_once_per_kind(self):
        plants = self.collection("--at", END)["plants"]
        for kind, label in (("trip", "Tripped"), ("derate", "Derated"), ("online", "Back online")):
            self.assertIn('data-status="%s"' % kind, plants["sum"])
            self.assertIn(">%s</span>" % label, plants["sum"])
        self.assertIn("gn-badge gn-badge--alert gn-sev", plants["lists"])
        # The status sorts by its rank, not by its words.
        self.assertIn('data-value="3"', plants["lists"])

    def test_the_profile_anchor_names_the_status_and_its_notice(self):
        pedc = self.profile("08PEDC", "--at", END)
        self.assertIn("Back online", pedc["plants"]["status"])
        self.assertIn("V155556", pedc["plants"]["latest"])
        self.assertEqual("08PEDC", pedc["profile"]["crumb"])
        self.assertIn("Which notices", pedc["profile"]["messages_filter"])


class PlantPageTests(unittest.TestCase):

    def test_the_pages_carry_the_new_blocks_and_no_inline_style(self):
        for name, ids in (("assets.html", ("status", "as-of", "status-sum", "status-list",
                                           "unclear-list", "only-notice", "filters")),
                          ("asset.html", ("activity", "activity-at", "activity-status",
                                          "activity-latest", "activity-facts", "watch", "next",
                                          "activity-unclear", "activity-src", "crumb"))):
            body = (GRID / name).read_text(encoding="utf-8")
            for element in ids:
                self.assertIn(f'id="{element}"', body, (name, element))
            self.assertNotIn("style=", body, name)
            self.assertNotIn("<style", body, name)
            self.assertNotIn("<script>", body, name)
        # Sam's ask panel keeps its mount on the profile page.
        self.assertIn('<section id="ask" data-context="asset"', (GRID / "asset.html").read_text(encoding="utf-8"))

    def test_the_script_sets_no_inline_style(self):
        script = (GRID / "asset.js").read_text(encoding="utf-8")
        self.assertNotIn("style=", script)
        self.assertNotIn(".style.", script)


if __name__ == "__main__":
    unittest.main()
