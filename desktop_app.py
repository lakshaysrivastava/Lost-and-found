# ============================================================
# app.py
# Lost and Found Management System - College Mini Project
# GUI built with Tkinter, data stored in MySQL.
#
# Run this file to start the application:
#     python app.py
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import db  # our database helper module

CATEGORIES = ["Electronics", "Books", "Stationery", "ID Card", "Bag",
              "Accessories", "Clothing", "Other"]


# ================================================================
# LOGIN WINDOW
# ================================================================
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lost and Found Management System - Login")
        self.geometry("400x260")
        self.resizable(False, False)
        self.configure(bg="#f0f4f8")

        tk.Label(self, text="Lost & Found Management System",
                  font=("Segoe UI", 14, "bold"), bg="#f0f4f8",
                  fg="#1a3c6e").pack(pady=(25, 5))
        tk.Label(self, text="Admin Login", font=("Segoe UI", 11),
                  bg="#f0f4f8").pack(pady=(0, 15))

        form = tk.Frame(self, bg="#f0f4f8")
        form.pack()

        tk.Label(form, text="Username:", bg="#f0f4f8").grid(row=0, column=0, padx=8, pady=8, sticky="e")
        self.username_entry = tk.Entry(form, width=25)
        self.username_entry.grid(row=0, column=1, padx=8, pady=8)
        self.username_entry.insert(0, "admin")

        tk.Label(form, text="Password:", bg="#f0f4f8").grid(row=1, column=0, padx=8, pady=8, sticky="e")
        self.password_entry = tk.Entry(form, width=25, show="*")
        self.password_entry.grid(row=1, column=1, padx=8, pady=8)

        tk.Button(self, text="Login", width=15, bg="#1a3c6e", fg="white",
                  command=self.try_login).pack(pady=10)

        tk.Label(self, text="Default: admin / admin123", fg="gray",
                  bg="#f0f4f8", font=("Segoe UI", 8)).pack()

        self.bind("<Return>", lambda event: self.try_login())

    def try_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        try:
            ok = db.verify_admin(username, password)
        except Exception as e:
            messagebox.showerror("Database Error",
                                  f"Could not connect to the database.\n\n{e}")
            return

        if ok:
            self.destroy()
            MainApp().mainloop()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")


# ================================================================
# MAIN APPLICATION WINDOW
# ================================================================
class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lost and Found Management System")
        self.geometry("950x600")

        style = ttk.Style(self)
        style.theme_use("clam")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.dashboard_tab = DashboardTab(notebook)
        self.lost_tab = LostItemsTab(notebook)
        self.found_tab = FoundItemsTab(notebook)
        self.search_tab = SearchMatchTab(notebook)

        notebook.add(self.dashboard_tab, text="  Dashboard  ")
        notebook.add(self.lost_tab, text="  Report Lost Item  ")
        notebook.add(self.found_tab, text="  Report Found Item  ")
        notebook.add(self.search_tab, text="  Search & Match  ")

        # Refresh dashboard stats whenever a tab is clicked
        notebook.bind("<<NotebookTabChanged>>", lambda e: self.dashboard_tab.refresh())


# ================================================================
# DASHBOARD TAB
# ================================================================
class DashboardTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="white")
        tk.Label(self, text="Overview", font=("Segoe UI", 16, "bold"),
                  bg="white").pack(pady=15)

        self.cards_frame = tk.Frame(self, bg="white")
        self.cards_frame.pack(pady=10)

        tk.Button(self, text="Refresh", command=self.refresh).pack(pady=10)

        self.card_labels = {}
        self.build_cards()
        self.refresh()

    def build_cards(self):
        card_info = [
            ("total_lost", "Total Lost Reports", "#c0392b"),
            ("total_found", "Total Found Reports", "#27ae60"),
            ("lost_pending", "Lost - Pending", "#e67e22"),
            ("found_pending", "Found - Pending", "#e67e22"),
            ("lost_claimed", "Lost - Claimed", "#2980b9"),
            ("found_claimed", "Found - Claimed", "#2980b9"),
        ]
        for i, (key, label, color) in enumerate(card_info):
            frame = tk.Frame(self.cards_frame, bg=color, width=180, height=90)
            frame.grid(row=i // 3, column=i % 3, padx=12, pady=12)
            frame.pack_propagate(False)
            value_lbl = tk.Label(frame, text="0", font=("Segoe UI", 20, "bold"),
                                  bg=color, fg="white")
            value_lbl.pack(pady=(15, 0))
            tk.Label(frame, text=label, bg=color, fg="white",
                      font=("Segoe UI", 9)).pack()
            self.card_labels[key] = value_lbl

    def refresh(self):
        try:
            stats = db.get_stats()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return
        for key, lbl in self.card_labels.items():
            lbl.config(text=str(stats.get(key, 0)))


# ================================================================
# REPORT LOST ITEM TAB
# ================================================================
class LostItemsTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.build_form()
        self.build_table()
        self.refresh_table()

    def build_form(self):
        form = tk.LabelFrame(self, text="Report a Lost Item", padx=10, pady=10)
        form.pack(fill="x", padx=10, pady=10)

        labels = ["Item Name*", "Category", "Description", "Location Lost",
                  "Date Lost (YYYY-MM-DD)", "Reporter Name*", "Contact Number*"]
        self.entries = {}

        for i, text in enumerate(labels):
            tk.Label(form, text=text).grid(row=i // 2, column=(i % 2) * 2,
                                            sticky="e", padx=5, pady=5)

        self.item_name = tk.Entry(form, width=25)
        self.item_name.grid(row=0, column=1, padx=5, pady=5)

        self.category = ttk.Combobox(form, values=CATEGORIES, width=22, state="readonly")
        self.category.grid(row=0, column=3, padx=5, pady=5)

        self.description = tk.Entry(form, width=25)
        self.description.grid(row=1, column=1, padx=5, pady=5)

        self.location = tk.Entry(form, width=25)
        self.location.grid(row=1, column=3, padx=5, pady=5)

        self.date_lost = tk.Entry(form, width=25)
        self.date_lost.insert(0, str(date.today()))
        self.date_lost.grid(row=2, column=1, padx=5, pady=5)

        self.reporter_name = tk.Entry(form, width=25)
        self.reporter_name.grid(row=2, column=3, padx=5, pady=5)

        self.reporter_contact = tk.Entry(form, width=25)
        self.reporter_contact.grid(row=3, column=1, padx=5, pady=5)

        tk.Button(form, text="Submit Report", bg="#1a3c6e", fg="white",
                  command=self.submit).grid(row=3, column=3, padx=5, pady=5, sticky="w")

    def submit(self):
        name = self.item_name.get().strip()
        reporter = self.reporter_name.get().strip()
        contact = self.reporter_contact.get().strip()

        if not name or not reporter or not contact:
            messagebox.showwarning("Missing Data",
                                    "Item Name, Reporter Name and Contact are required.")
            return

        try:
            db.add_lost_item(
                name, self.category.get(), self.description.get().strip(),
                self.location.get().strip(), self.date_lost.get().strip(),
                reporter, contact,
            )
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return

        messagebox.showinfo("Success", "Lost item reported successfully.")
        self.clear_form()
        self.refresh_table()

    def clear_form(self):
        for widget in (self.item_name, self.description, self.location,
                       self.reporter_name, self.reporter_contact):
            widget.delete(0, tk.END)
        self.category.set("")
        self.date_lost.delete(0, tk.END)
        self.date_lost.insert(0, str(date.today()))

    def build_table(self):
        table_frame = tk.LabelFrame(self, text="All Lost Item Reports", padx=5, pady=5)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("ID", "Item", "Category", "Location", "Date",
                   "Reporter", "Contact", "Status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Refresh", command=self.refresh_table).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Mark Claimed", command=self.mark_claimed).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=5)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            rows = db.get_all_lost_items()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return
        for row in rows:
            self.tree.insert("", "end", values=row)

    def get_selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a row first.")
            return None
        return self.tree.item(selected[0])["values"][0]

    def mark_claimed(self):
        item_id = self.get_selected_id()
        if item_id is None:
            return
        db.update_lost_status(item_id, "Claimed")
        self.refresh_table()

    def delete_selected(self):
        item_id = self.get_selected_id()
        if item_id is None:
            return
        if messagebox.askyesno("Confirm Delete", "Delete this lost item record?"):
            db.delete_lost_item(item_id)
            self.refresh_table()


# ================================================================
# REPORT FOUND ITEM TAB (mirrors LostItemsTab)
# ================================================================
class FoundItemsTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.build_form()
        self.build_table()
        self.refresh_table()

    def build_form(self):
        form = tk.LabelFrame(self, text="Report a Found Item", padx=10, pady=10)
        form.pack(fill="x", padx=10, pady=10)

        labels = ["Item Name*", "Category", "Description", "Location Found",
                  "Date Found (YYYY-MM-DD)", "Founder Name*", "Contact Number*"]
        for i, text in enumerate(labels):
            tk.Label(form, text=text).grid(row=i // 2, column=(i % 2) * 2,
                                            sticky="e", padx=5, pady=5)

        self.item_name = tk.Entry(form, width=25)
        self.item_name.grid(row=0, column=1, padx=5, pady=5)

        self.category = ttk.Combobox(form, values=CATEGORIES, width=22, state="readonly")
        self.category.grid(row=0, column=3, padx=5, pady=5)

        self.description = tk.Entry(form, width=25)
        self.description.grid(row=1, column=1, padx=5, pady=5)

        self.location = tk.Entry(form, width=25)
        self.location.grid(row=1, column=3, padx=5, pady=5)

        self.date_found = tk.Entry(form, width=25)
        self.date_found.insert(0, str(date.today()))
        self.date_found.grid(row=2, column=1, padx=5, pady=5)

        self.founder_name = tk.Entry(form, width=25)
        self.founder_name.grid(row=2, column=3, padx=5, pady=5)

        self.founder_contact = tk.Entry(form, width=25)
        self.founder_contact.grid(row=3, column=1, padx=5, pady=5)

        tk.Button(form, text="Submit Report", bg="#1a6e3c", fg="white",
                  command=self.submit).grid(row=3, column=3, padx=5, pady=5, sticky="w")

    def submit(self):
        name = self.item_name.get().strip()
        founder = self.founder_name.get().strip()
        contact = self.founder_contact.get().strip()

        if not name or not founder or not contact:
            messagebox.showwarning("Missing Data",
                                    "Item Name, Founder Name and Contact are required.")
            return

        try:
            db.add_found_item(
                name, self.category.get(), self.description.get().strip(),
                self.location.get().strip(), self.date_found.get().strip(),
                founder, contact,
            )
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return

        messagebox.showinfo("Success", "Found item reported successfully.")
        self.clear_form()
        self.refresh_table()

    def clear_form(self):
        for widget in (self.item_name, self.description, self.location,
                       self.founder_name, self.founder_contact):
            widget.delete(0, tk.END)
        self.category.set("")
        self.date_found.delete(0, tk.END)
        self.date_found.insert(0, str(date.today()))

    def build_table(self):
        table_frame = tk.LabelFrame(self, text="All Found Item Reports", padx=5, pady=5)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("ID", "Item", "Category", "Location", "Date",
                   "Founder", "Contact", "Status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Refresh", command=self.refresh_table).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Mark Claimed", command=self.mark_claimed).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=5)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            rows = db.get_all_found_items()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return
        for row in rows:
            self.tree.insert("", "end", values=row)

    def get_selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a row first.")
            return None
        return self.tree.item(selected[0])["values"][0]

    def mark_claimed(self):
        item_id = self.get_selected_id()
        if item_id is None:
            return
        db.update_found_status(item_id, "Claimed")
        self.refresh_table()

    def delete_selected(self):
        item_id = self.get_selected_id()
        if item_id is None:
            return
        if messagebox.askyesno("Confirm Delete", "Delete this found item record?"):
            db.delete_found_item(item_id)
            self.refresh_table()


# ================================================================
# SEARCH & MATCH TAB
# ================================================================
class SearchMatchTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        search_frame = tk.Frame(self)
        search_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(search_frame, text="Search keyword (item name / category / location):").pack(side="left")
        self.search_entry = tk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=8)
        tk.Button(search_frame, text="Search", command=self.do_search).pack(side="left", padx=5)
        tk.Button(search_frame, text="Show Possible Matches", command=self.show_matches).pack(side="left", padx=15)

        results_frame = tk.LabelFrame(self, text="Results")
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("Type", "ID", "Item", "Category", "Location/Date",
                   "Person", "Contact", "Status")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=12)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        tk.Label(self, text="Tip: select one 'Lost' row and one 'Found' row, then click "
                            "'Mark Selected as Claimed / Returned'.",
                  fg="gray").pack(pady=(0, 5))
        tk.Button(self, text="Mark Selected as Claimed / Returned",
                  command=self.mark_claimed).pack(pady=5)

    def clear_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def do_search(self):
        keyword = self.search_entry.get().strip()
        if not keyword:
            messagebox.showwarning("Missing keyword", "Please type something to search.")
            return
        self.clear_tree()
        try:
            for row in db.search_lost(keyword):
                self.tree.insert("", "end", values=("Lost",) + row)
            for row in db.search_found(keyword):
                self.tree.insert("", "end", values=("Found",) + row)
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def show_matches(self):
        self.clear_tree()
        try:
            matches = db.find_possible_matches()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return

        if not matches:
            messagebox.showinfo("No Matches", "No possible matches found right now.")
            return

        for (lost_id, l_name, l_cat, l_reporter,
             found_id, f_name, f_cat, f_founder) in matches:
            self.tree.insert("", "end", values=("Lost", lost_id, l_name, l_cat,
                                                 "-", l_reporter, "-", "Pending"))
            self.tree.insert("", "end", values=("Found", found_id, f_name, f_cat,
                                                 "-", f_founder, "-", "Pending"))

    def mark_claimed(self):
        selected = self.tree.selection()
        if len(selected) != 2:
            messagebox.showwarning("Select Two Rows",
                                    "Please select exactly one 'Lost' row and one 'Found' row.")
            return

        row1 = self.tree.item(selected[0])["values"]
        row2 = self.tree.item(selected[1])["values"]

        if row1[0] == row2[0]:
            messagebox.showwarning("Invalid Selection",
                                    "You must select one Lost item and one Found item.")
            return

        lost_row = row1 if row1[0] == "Lost" else row2
        found_row = row1 if row1[0] == "Found" else row2

        try:
            db.mark_as_claimed(lost_row[1], found_row[1])
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return

        messagebox.showinfo("Success", "Item marked as claimed/returned successfully.")
        self.clear_tree()


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    login = LoginWindow()
    login.mainloop()
