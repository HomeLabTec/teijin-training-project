from flask import Flask, render_template, request, jsonify, redirect, url_for
import openpyxl
import os

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "training-master.xlsx")

def load_workbook_data():
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    # detect skill columns (every other starting at C = 3)
    headers = []
    for skill_col in range(3, ws.max_column + 1, 2):
        meta_col = skill_col - 1
        # pull part name from row 1, part number from row 2
        part_name   = ws.cell(row=1, column=meta_col).value or ""
        part_number = ws.cell(row=2, column=meta_col).value or ""
        # build a display string: "Name (Number)" or fallback to whichever
        if part_name and part_number:
            display = f"{part_name} ({part_number})"
        else:
            display = part_name or str(part_number)
        headers.append((skill_col, display))

    # build data dict: { name → { display → level, … } }
    data = {}
    for row in range(3, ws.max_row + 1):
        name = ws.cell(row=row, column=1).value
        if not name:
            continue
        skills = {}
        for col, display in headers:
            raw = ws.cell(row=row, column=col).value
            skills[display] = int(raw) if (raw is not None) else 1
        data[name] = skills

    return wb, ws, headers, data


app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/display")
def display():
    # load headers & data as before
    wb, ws, headers, data = load_workbook_data()
    parts = [part for _, part in headers]
    return render_template("display.html", parts=parts, data=data)


@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    _, _, _, data = load_workbook_data()
    matches = [n for n in data if q in n.lower()]
    return jsonify(matches)

@app.route("/person/<name>", methods=["GET", "POST"])
def person(name):
    wb, ws, headers, data = load_workbook_data()

    if request.method == "POST":
        # ---- Handle Delete ----
        if request.form.get("action") == "delete":
            # find the row for this person and delete it
            for row in range(3, ws.max_row + 1):
                if ws.cell(row=row, column=1).value == name:
                    ws.delete_rows(row, 1)
                    wb.save(EXCEL_PATH)
                    break
            return redirect(url_for("index"))

        # ---- Otherwise Handle Update ----
        for col, part in headers:
            new_val = int(request.form.get(part, 1))
            for row in range(3, ws.max_row + 1):
                if ws.cell(row=row, column=1).value == name:
                    ws.cell(row=row, column=col, value=new_val)
                    break
        wb.save(EXCEL_PATH)
        return redirect(url_for("person", name=name))

    skills = data.get(name)
    if skills is None:
        return "Not found", 404

    parts = [p for _, p in headers]
    return render_template("person.html", name=name, parts=parts, skills=skills)


@app.route("/add", methods=["GET", "POST"])
def add():
    wb, ws, headers, _ = load_workbook_data()
    parts = [p for _, p in headers]

    if request.method == "POST":
        name = request.form["name"].strip()
        new_row = ws.max_row + 1
        ws.cell(row=new_row, column=1, value=name)
        for col, part in headers:
            ws.cell(row=new_row, column=col, value=int(request.form.get(part, 1)))
        wb.save(EXCEL_PATH)
        return redirect(url_for("index"))

    return render_template("add.html", parts=parts)

@app.route("/decrease", methods=["GET", "POST"])
def decrease():
    wb, ws, headers, _ = load_workbook_data()
    parts = [p for _, p in headers]

    if request.method == "POST":
        part   = request.form["part"]
        amount = int(request.form["amount"])
        col = next(c for c, p in headers if p == part)
        for row in range(3, ws.max_row + 1):
            cur = ws.cell(row=row, column=col).value or 1
            ws.cell(row=row, column=col, value=max(1, cur - amount))
        wb.save(EXCEL_PATH)
        return redirect(url_for("index"))

    return render_template("decrease.html", parts=parts)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
