import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Dict, Optional


class MedicineManagementFeature:
    MEDICINE_CATALOG: Dict[str, Dict[str, str]] = {
        "Paracetamol": {
            "brands": "Biogesic, Tempra, Calpol",
            "use": "Pain or fever relief",
            "strengths": "120 mg/5 mL liquid, 250 mg/5 mL liquid, 500 mg tablet",
        },
        "Ibuprofen": {
            "brands": "Advil, Alaxan",
            "use": "Pain, fever, or inflammation relief",
            "strengths": "100 mg/5 mL liquid, 200 mg tablet, 400 mg tablet",
        },
        "Mefenamic Acid": {
            "brands": "Ponstan",
            "use": "Pain relief",
            "strengths": "250 mg capsule, 500 mg capsule",
        },
        "Cetirizine": {
            "brands": "Alizer, Zyrtec",
            "use": "Allergy symptoms and itchiness",
            "strengths": "5 mg tablet, 10 mg tablet, 5 mg/5 mL liquid",
        },
        "Loratadine": {
            "brands": "Claritin",
            "use": "Allergy symptom relief",
            "strengths": "10 mg tablet, 5 mg/5 mL liquid",
        },
        "Dextromethorphan": {
            "brands": "Robitussin",
            "use": "Dry cough relief",
            "strengths": "Product strength varies; check the package label",
        },
        "Ambroxol": {
            "brands": "Expel",
            "use": "Helps loosen mucus",
            "strengths": "30 mg tablet, 15 mg/5 mL liquid",
        },
        "Amlodipine": {
            "brands": "Norvasc",
            "use": "High blood pressure",
            "strengths": "2.5 mg tablet, 5 mg tablet, 10 mg tablet",
        },
        "Losartan": {
            "brands": "Cozaar",
            "use": "High blood pressure",
            "strengths": "25 mg tablet, 50 mg tablet, 100 mg tablet",
        },
        "Atorvastatin": {
            "brands": "Lipitor",
            "use": "High cholesterol",
            "strengths": "10 mg tablet, 20 mg tablet, 40 mg tablet, 80 mg tablet",
        },
        "Omeprazole": {
            "brands": "Losec, Prilosec",
            "use": "Hyperacidity, GERD, or ulcers",
            "strengths": "10 mg capsule, 20 mg capsule, 40 mg capsule",
        },
        "Loperamide": {
            "brands": "Imodium",
            "use": "Diarrhea",
            "strengths": "2 mg capsule or tablet",
        },
        "Aluminum Hydroxide + Magnesium Hydroxide": {
            "brands": "Kremil-S",
            "use": "Heartburn or hyperacidity",
            "strengths": "Combination strength varies; check the product label",
        },
    }
    CUSTOM_MEDICINE_OPTION = "Other / Custom medicine"
    CUSTOM_STRENGTH_OPTION = "Other / custom strength"

    def _create_tab_medicine(self, notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=self.tabs[1])

        left = ttk.LabelFrame(frame, text="Add Medicine", padding=12)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(left, text="Patient").grid(row=0, column=0, sticky="w", pady=4)
        self.medicine_patient = ttk.Combobox(left, state="readonly", width=28)
        self.medicine_patient.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(left, text="Select medicine").grid(row=1, column=0, sticky="w", pady=4)
        self.medicine_name = ttk.Combobox(
            left,
            state="readonly",
            width=28,
            values=(*self.MEDICINE_CATALOG, self.CUSTOM_MEDICINE_OPTION),
        )
        self.medicine_name.grid(row=1, column=1, padx=5, pady=4)
        self.medicine_name.bind("<<ComboboxSelected>>", self._update_medicine_catalog_details)

        self.medicine_catalog_details = tk.StringVar(value="Select a medicine for brand and use details.")
        ttk.Label(
            left,
            textvariable=self.medicine_catalog_details,
            wraplength=300,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(left, text="Select prescribed strength").grid(row=3, column=0, sticky="w", pady=4)
        self.medicine_dosage = ttk.Combobox(left, state="readonly", width=28)
        self.medicine_dosage.grid(row=3, column=1, padx=5, pady=4)
        self.medicine_dosage.bind("<<ComboboxSelected>>", self._select_medicine_strength)

        ttk.Label(left, text="Reminder Time").grid(row=4, column=0, sticky="w", pady=4)
        self.medicine_time = ttk.Entry(left, width=30)
        self.medicine_time.insert(0, "08:00")
        self.medicine_time.grid(row=4, column=1, padx=5, pady=4)

        ttk.Label(left, text="Notes").grid(row=5, column=0, sticky="w", pady=4)
        self.medicine_notes = ttk.Entry(left, width=30)
        self.medicine_notes.grid(row=5, column=1, padx=5, pady=4)

        ttk.Label(
            left,
            text="Strength examples only. Follow the patient's prescription and exact package label.",
            wraplength=300,
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 8))

        ttk.Button(left, text="Add Medicine", command=self.add_medicine).grid(row=7, column=0, columnspan=2, pady=10)
        medicine_actions = ttk.Frame(left)
        medicine_actions.grid(row=8, column=0, columnspan=2, pady=(0, 4))
        ttk.Button(medicine_actions, text="Update Selected", command=self.update_medicine).pack(side="left", padx=3)
        ttk.Button(medicine_actions, text="Delete Selected", command=self.delete_medicine).pack(side="left", padx=3)

        right = ttk.LabelFrame(frame, text="Current Medicines", padding=10)
        right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        cols = ("ID", "Patient", "Medicine", "Dosage", "Reminder", "Status")
        self.medicine_tree = ttk.Treeview(right, columns=cols, show="headings")
        for col in cols:
            self.medicine_tree.heading(col, text=col)
            self.medicine_tree.column(col, width=120, anchor="center")
        self.medicine_tree.pack(fill="both", expand=True)
        self.medicine_tree.bind("<<TreeviewSelect>>", self._select_medicine)

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

    def _update_medicine_catalog_details(self, _event=None) -> None:
        medicine_name = self.medicine_name.get().strip()
        if medicine_name == self.CUSTOM_MEDICINE_OPTION:
            self.medicine_name.configure(state="normal")
            self.medicine_name.set("")
            self.medicine_dosage.configure(state="normal")
            self.medicine_dosage.set("")
            self.medicine_dosage["values"] = ()
            self.medicine_catalog_details.set(
                "Enter a custom medicine name and the prescribed strength from its label or prescription."
            )
            return

        details = self.MEDICINE_CATALOG.get(medicine_name)
        if details is None:
            self.medicine_name.configure(state="normal")
            self.medicine_catalog_details.set(
                "Custom medicine. Confirm its details against the prescription or product label."
            )
            self.medicine_dosage.configure(state="normal")
            self.medicine_dosage["values"] = ()
            return

        self.medicine_name.configure(state="readonly")
        self.medicine_dosage.configure(state="readonly")
        self.medicine_catalog_details.set(
            f"Brands: {details['brands']}\nUse: {details['use']}"
        )
        strengths = tuple(
            strength.strip()
            for strength in details["strengths"].split(",")
        )
        self.medicine_dosage["values"] = (*strengths, self.CUSTOM_STRENGTH_OPTION)
        self.medicine_dosage.set("")

    def _select_medicine_strength(self, _event=None) -> None:
        if self.medicine_dosage.get() == self.CUSTOM_STRENGTH_OPTION:
            self.medicine_dosage.configure(state="normal")
            self.medicine_dosage.set("")

    def _refresh_medicine_tree(self) -> None:
        for row in self.medicine_tree.get_children():
            self.medicine_tree.delete(row)
        for med in self.get_medicines():
            self.medicine_tree.insert(
                "",
                "end",
                values=(
                    med["id"],
                    med["patient_name"],
                    med["medicine_name"],
                    med["dosage"],
                    med["reminder_time"],
                    med["today_status"] or "pending",
                ),
            )

    def add_medicine(self) -> None:
        patient_value = self.medicine_patient.get().strip()
        medicine_name = self.medicine_name.get().strip()
        dosage = self.medicine_dosage.get().strip()
        reminder_time = self.medicine_time.get().strip()
        notes = self.medicine_notes.get().strip()

        if not patient_value or not medicine_name or not dosage:
            messagebox.showerror("Required fields", "Please select a patient and fill medicine details.")
            return
        if reminder_time:
            try:
                reminder_time = datetime.strptime(reminder_time, "%H:%M").strftime("%H:%M")
            except ValueError:
                messagebox.showerror("Invalid time", "Enter the reminder time in 24-hour HH:MM format.")
                return

        patient_id = int(patient_value.split(" - ")[0])
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO medicines (patient_id, medicine_name, dosage, reminder_time, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (patient_id, medicine_name, dosage, reminder_time or "08:00", "pending", notes or "Medication plan"),
            )
            conn.commit()
        finally:
            conn.close()

        self.medicine_name.set("")
        self.medicine_name.configure(state="readonly")
        self.medicine_dosage.delete(0, tk.END)
        self.medicine_dosage.configure(state="readonly")
        self.medicine_dosage["values"] = ()
        self.medicine_time.delete(0, tk.END)
        self.medicine_time.insert(0, "08:00")
        self.medicine_notes.delete(0, tk.END)
        self.medicine_catalog_details.set("Select a medicine for brand and use details.")
        self.refresh_all()
        messagebox.showinfo("Success", "Medicine added successfully.")

    def _select_medicine(self, _event=None) -> None:
        selection = self.medicine_tree.selection()
        if not selection:
            self.selected_medicine_id = None
            return

        values = self.medicine_tree.item(selection[0], "values")
        self.selected_medicine_id = int(values[0])
        patient_id, notes = self._medicine_edit_details(self.selected_medicine_id)
        self.medicine_patient.set(f"{patient_id} - {values[1]}")
        self.medicine_name.set(values[2])
        self._update_medicine_catalog_details()
        if values[3] in self.medicine_dosage["values"]:
            self.medicine_dosage.set(values[3])
        else:
            self.medicine_dosage.configure(state="normal")
            self.medicine_dosage.set(values[3])
        self.medicine_time.delete(0, tk.END)
        self.medicine_time.insert(0, values[4] or "")
        self.medicine_notes.delete(0, tk.END)
        self.medicine_notes.insert(0, notes or "")

    def _medicine_edit_details(self, medicine_id: int) -> tuple[int, Optional[str]]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT patient_id, notes FROM medicines WHERE id = ?",
                (medicine_id,),
            ).fetchone()
            if row is None:
                raise ValueError("The selected medicine no longer exists.")
            return int(row["patient_id"]), row["notes"]
        finally:
            conn.close()

    def update_medicine(self) -> None:
        if self.selected_medicine_id is None:
            messagebox.showinfo("Select medicine", "Select a medicine from the list before updating it.")
            return

        patient_value = self.medicine_patient.get().strip()
        medicine_name = self.medicine_name.get().strip()
        dosage = self.medicine_dosage.get().strip()
        reminder_time = self.medicine_time.get().strip()
        notes = self.medicine_notes.get().strip()
        if not patient_value or not medicine_name or not dosage:
            messagebox.showerror("Required fields", "Please select a patient and enter the medicine name and dosage.")
            return
        if reminder_time:
            try:
                reminder_time = datetime.strptime(reminder_time, "%H:%M").strftime("%H:%M")
            except ValueError:
                messagebox.showerror("Invalid time", "Enter the reminder time in 24-hour HH:MM format.")
                return

        patient_id = int(patient_value.split(" - ", 1)[0])
        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE medicines
                SET patient_id = ?, medicine_name = ?, dosage = ?, reminder_time = ?, notes = ?
                WHERE id = ?
                """,
                (patient_id, medicine_name, dosage, reminder_time or "08:00", notes, self.selected_medicine_id),
            )
            conn.commit()
        finally:
            conn.close()

        self.selected_medicine_id = None
        self.refresh_all()
        messagebox.showinfo("Updated", "Medicine details updated successfully.")

    def delete_medicine(self) -> None:
        if self.selected_medicine_id is None:
            messagebox.showinfo("Select medicine", "Select a medicine from the list before deleting it.")
            return
        if not messagebox.askyesno(
            "Delete medicine",
            "Delete this medicine? Its medication history will be kept.",
        ):
            return

        conn = self._connect()
        try:
            conn.execute("DELETE FROM medicines WHERE id = ?", (self.selected_medicine_id,))
            conn.commit()
        finally:
            conn.close()

        self.selected_medicine_id = None
        self.refresh_all()
        messagebox.showinfo("Deleted", "Medicine deleted. Its medication history is still available.")
