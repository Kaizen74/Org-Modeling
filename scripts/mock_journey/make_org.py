"""
SAMPLE DATA — a fictional 141-person organization built to exercise edge cases:
duplicate names, two managers sharing a name, a Level-column mismatch, missing
salaries (filled from grades), team leads tagged Operational in the Work Type
column, Windows-1252 characters. The same seed always gives the same file.
Usage: python make_org.py <out.csv>
"""
import csv, io, random, sys

random.seed(11)
rows = []
n = [0]


def add(name, title, grade, dept, level, mgr, salary, wa="", work_type=""):
    n[0] += 1
    eid = f"T{n[0]:03d}"
    rows.append([name, title, grade, dept, level, mgr, salary, eid, wa, work_type])
    return eid


add("Alicia Seah", "Chief Executive Officer", "SVP", "Executive", 1, "Top of Org", 420000, "Sets strategy")
add("Tan Boon Hock", "VP, Ground Operations", "H8", "Ground Operations", 2, "Alicia Seah", 260000, "Runs ramp and baggage")
for d in ["Ramp", "Baggage", "Cargo"]:
    m = f"Manager {d}"
    add(m, f"Manager, {d} Operations", "H6", "Ground Operations", 3, "Tan Boon Hock", "", f"Plans {d.lower()} shifts")  # no salary
    for t in range(2):
        tl = f"{d} Lead {t}"
        add(tl, f"{d} Team Lead", "TL", "Ground Operations", 4, m, 85000, f"Supervises {d.lower()} crew", "operational")
        for a in range(random.randint(12, 16)):
            add(f"{d} Agent {t}-{a}", f"{d} Services Agent", "AO", "Ground Operations", 5, tl, 48000, f"{d} handling, loading")
add("Jasmine Lim", "VP, Customer Experience", "H8", "Customer Experience", 2, "Alicia Seah", 250000, "CX strategy")
for area in ["CX Insights", "Service Design", "Loyalty"]:
    sm = f"Senior {area}"
    add(sm, f"Senior Manager, {area}", "H6", "Customer Experience", 3, "Jasmine Lim", 170000, f"{area} programmes, stakeholder reporting")
    mm = f"Mgr {area}"
    add(mm, f"Manager, {area}", "H5", "Customer Experience", 4, sm, 130000, f"{area} analysis, stakeholder reporting")
    for a in range(3):
        add(f"{area} Analyst {a}", f"{area} Analyst", "AO", "Customer Experience", 5, mm, 72000, "Data analysis, stakeholder reporting")
add("Conor O’Brien", "Head, Strategic Communications", "H8", "Strategic Communications", 2, "Alicia Seah", 230000, "Corporate affairs, internal communications")
for t in ["Internal Communications", "Corporate Affairs"]:
    m = f"{t} Mgr"
    add(m, f"{t} Manager", "H5", "Strategic Communications", 3, "Conor O’Brien", 140000, t)
    for a in range(3):
        add(f"{t} Exec {a}", f"{t} Executive", "AO", "Strategic Communications", 4, m, 70000, t)
add("Rachel Ng", "CFO", "H8", "Finance", 2, "Alicia Seah", 280000, "Financial planning, reporting")
add("Kumar Raj", "Finance Manager", "H6", "Finance", 3, "Rachel Ng", 150000, "Budgeting, stakeholder reporting")
for a in range(6):
    add(f"Finance Exec {a}", "Finance Executive", "AO", "Finance", 4, "Kumar Raj", 68000, "Accounts payable, reporting")
add("Kumar Raj", "Finance Analyst", "AO", "Finance", 3, "Rachel Ng", 66000, "Financial analysis")  # same name as the manager
add("Wei Tan", "Head, People", "H8", "People", 2, "Alicia Seah", 220000, "HR strategy")
hrbp = add("Wei Tan", "HR Business Partner", "H5", "People", 3, "Wei Tan", 120000, "Partnering")  # shares a name with own manager
add("Mei Lin", "HR Executive", "AO", "People", 3, hrbp, 65000, "Payroll, onboarding")  # manager given by Employee ID; Level says 3, actually layer 4

buf = io.StringIO()
w = csv.writer(buf)
w.writerow(["Name", "Job Title", "Grade", "Department", "Level", "Line Manager", "Salary", "Employee ID", "Work Activities", "Work Type"])
w.writerows(rows)
open(sys.argv[1], "wb").write(buf.getvalue().encode("cp1252"))  # Excel's default encoding
print(len(rows))
