"""
Developed by MASA
All Rights Reserved.
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import matplotlib.pyplot as plt

conn = sqlite3.connect("expense_budget.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    description TEXT,
    amount REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS budget (
    id INTEGER PRIMARY KEY,
    monthly_budget REAL,
    month TEXT
)
""")

cur.execute(
    """
INSERT OR IGNORE INTO budget (id, monthly_budget, month)
VALUES (1, 0, ?)
""",
    (datetime.now().strftime("%Y-%m"),),
)
conn.commit()


def current_month():
    return datetime.now().strftime("%Y-%m")


def reset_if_new_month():
    cur.execute("SELECT month FROM budget WHERE id=1")
    saved_month = cur.fetchone()[0]

    if saved_month != current_month():
        cur.execute("DELETE FROM expenses")
        cur.execute("UPDATE budget SET month=?, monthly_budget=0 WHERE id=1", (current_month(),))
        conn.commit()


def clear_fields():
    date_var.set(date.today())
    desc_var.set("")
    amount_var.set("")


def update_totals():
    cur.execute("SELECT SUM(amount) FROM expenses")
    total_expenses = cur.fetchone()[0] or 0

    cur.execute("SELECT monthly_budget FROM budget WHERE id=1")
    budget_remaining = cur.fetchone()[0]

    total_lbl.config(text=f"Total Expenses: ${total_expenses:.2f}")
    remaining_lbl.config(text=f"Remaining Budget: ${budget_remaining:.2f}")

    budget_lbl.config(text=f"Monthly Budget: ${budget_remaining + total_expenses:.2f}")

    if budget_remaining < 0:
        remaining_lbl.config(fg="red")
    elif budget_remaining <= 0.3 * (budget_remaining + total_expenses):
        remaining_lbl.config(fg="orange")
    else:
        remaining_lbl.config(fg="green")


def load_data():
    reset_if_new_month()
    tree.delete(*tree.get_children())

    cur.execute("SELECT * FROM expenses")
    for row in cur.fetchall():
        tree.insert("", tk.END, values=row)

    update_totals()


def add_expense():
    if not desc_var.get() or not amount_var.get():
        messagebox.showwarning("Input Error", "All fields required")
        return
    try:
        amount = float(amount_var.get())
    except ValueError:
        messagebox.showerror("Error", "Amount must be numeric")
        return

    cur.execute(
        "INSERT INTO expenses (date, description, amount) VALUES (?, ?, ?)",
        (date_var.get(), desc_var.get(), amount),
    )

    cur.execute("UPDATE budget SET monthly_budget = monthly_budget - ? WHERE id=1", (amount,))
    conn.commit()
    clear_fields()
    load_data()


def update_expense():
    selected = tree.selection()
    if not selected:
        return

    expense_id = tree.item(selected[0])["values"][0]
    try:
        new_amount = float(amount_var.get())
    except ValueError:
        messagebox.showerror("Error", "Amount must be numeric")
        return

    old_amount = float(tree.item(selected[0])["values"][3])
    diff = new_amount - old_amount

    cur.execute(
        """
        UPDATE expenses SET date=?, description=?, amount=? WHERE id=?
    """,
        (date_var.get(), desc_var.get(), new_amount, expense_id),
    )

    cur.execute("UPDATE budget SET monthly_budget = monthly_budget - ? WHERE id=1", (diff,))
    conn.commit()
    clear_fields()
    load_data()


def delete_expense():
    selected = tree.selection()
    if not selected:
        return

    expense_id = tree.item(selected[0])["values"][0]
    amount = float(tree.item(selected[0])["values"][3])

    cur.execute("DELETE FROM expenses WHERE id=?", (expense_id,))

    cur.execute("UPDATE budget SET monthly_budget = monthly_budget + ? WHERE id=1", (amount,))
    conn.commit()
    clear_fields()
    load_data()


def select_item(event):
    selected = tree.selection()
    if selected:
        values = tree.item(selected[0])["values"]
        date_var.set(values[1])
        desc_var.set(values[2])
        amount_var.set(values[3])


def set_budget():
    try:
        budget = float(budget_var.get())
    except ValueError:
        messagebox.showerror("Error", "Budget must be numeric")
        return

    cur.execute(
        """
        UPDATE budget SET monthly_budget=?, month=? WHERE id=1
    """,
        (budget, current_month()),
    )
    conn.commit()
    update_totals()
    budget_var.set("")


def show_chart():
    cur.execute("SELECT date, amount FROM expenses")
    data = cur.fetchall()
    if not data:
        return

    dates = [d[0] for d in data]
    amounts = [a[1] for a in data]

    plt.clf()

    plt.bar(dates, amounts, color="skyblue")
    plt.title("MASA - Monthly Expenses")
    plt.ylabel("Amount ($)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def show_monthly_history():
    history_win = tk.Toplevel(root)
    history_win.title("MASA - Monthly History")
    history_win.geometry("600x400")

    columns = ("Month", "Total Expenses ($)")
    history_tree = ttk.Treeview(history_win, columns=columns, show="headings")
    history_tree.heading("Month", text="Month")
    history_tree.heading("Total Expenses ($)", text="Total Expenses ($)")
    history_tree.column("Month", anchor=tk.CENTER)
    history_tree.column("Total Expenses ($)", anchor=tk.CENTER)
    history_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    cur.execute("""
        SELECT strftime('%Y-%m', date) as month, SUM(amount) 
        FROM expenses 
        GROUP BY month 
        ORDER BY month ASC
    """)
    for row in cur.fetchall():
        history_tree.insert("", tk.END, values=row)


root = tk.Tk()
root.title("MASA - Daily Expense Tracker")
root.geometry("860x560")

date_var = tk.StringVar(value=date.today())
desc_var = tk.StringVar()
amount_var = tk.StringVar()
budget_var = tk.StringVar()

budget_frame = tk.LabelFrame(root, text="Monthly Budget", padx=10, pady=8)
budget_frame.pack(fill="x", padx=10, pady=5)

tk.Label(budget_frame, text="Set Budget ($):").pack(side=tk.LEFT)
tk.Entry(budget_frame, textvariable=budget_var, width=15).pack(side=tk.LEFT, padx=5)
tk.Button(budget_frame, text="Save Budget", command=set_budget).pack(side=tk.LEFT)
tk.Button(budget_frame, text="Show Chart", command=show_chart).pack(side=tk.RIGHT)
tk.Button(budget_frame, text="Monthly History", command=show_monthly_history).pack(side=tk.RIGHT, padx=5)

budget_lbl = tk.Label(budget_frame, text="Monthly Budget: $0.00", font=("Arial", 10, "bold"))
budget_lbl.pack(side=tk.RIGHT, padx=10)

input_frame = tk.LabelFrame(root, text="Expense Entry", padx=10, pady=10)
input_frame.pack(fill="x", padx=10)

tk.Label(input_frame, text="Date").grid(row=0, column=0)
tk.Label(input_frame, text="Description").grid(row=0, column=1)
tk.Label(input_frame, text="Amount ($)").grid(row=0, column=2)

tk.Entry(input_frame, textvariable=date_var, width=12).grid(row=1, column=0, padx=5)
tk.Entry(input_frame, textvariable=desc_var, width=30).grid(row=1, column=1, padx=5)
tk.Entry(input_frame, textvariable=amount_var, width=10).grid(row=1, column=2, padx=5)

tk.Button(input_frame, text="Add", width=10, command=add_expense).grid(row=1, column=3)
tk.Button(input_frame, text="Update", width=10, command=update_expense).grid(row=1, column=4)
tk.Button(input_frame, text="Delete", width=10, command=delete_expense).grid(row=1, column=5)

columns = ("ID", "Date", "Description", "Amount ($)")
tree = ttk.Treeview(root, columns=columns, show="headings")

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, anchor=tk.CENTER)

tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
tree.bind("<ButtonRelease-1>", select_item)

summary = tk.Frame(root)
summary.pack(fill="x", padx=10)

total_lbl = tk.Label(summary, text="Total Expenses: $0.00", font=("Arial", 11, "bold"))
total_lbl.pack(side=tk.LEFT)

remaining_lbl = tk.Label(summary, text="Remaining Budget: $0.00", font=("Arial", 11, "bold"))
remaining_lbl.pack(side=tk.RIGHT)

load_data()
root.mainloop()
conn.close()
