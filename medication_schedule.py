import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk


class MedicationScheduleFeature:
    def _create_tab_schedule(self, notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=self.tabs[3])

        left = ttk.LabelFrame(frame, text="Schedule Medication", padding=12)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(left, text="Patient").grid(row=0, column=0, sticky="w", pady=4)
        self.schedule_patient = ttk.Combobox(left, state="readonly", width=28)
        self.schedule_patient.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(left, text="Date").grid(row=1, column=0, sticky="w", pady=4)
        self.schedule_date = ttk.Entry(left, width=30)
        self.schedule_date.insert(0, datetime.today().strftime("%Y-%m-%d"))
        self.schedule_date.grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(left, text="Doctor").grid(row=2, column=0, sticky="w", pady=4)
        self.schedule_doctor = ttk.Entry(left, width=30)
        self.schedule_doctor.grid(row=2, column=1, padx=5, pady=4)

        ttk.Button(left, text="Save Schedule", command=self.save_schedule).grid(row=3, column=0, columnspan=2, pady=10)

        right = ttk.LabelFrame(frame, text="Upcoming Schedule", padding=10)
        right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        cols = ("Date", "Patient", "Doctor")
        self.schedule_tree = ttk.Treeview(right, columns=cols, show="headings")
        for col in cols:
            self.schedule_tree.heading(col, text=col)
            self.schedule_tree.column(col, width=160, anchor="center")
        self.schedule_tree.pack(fill="both", expand=True)

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

    def _refresh_schedule_tree(self) -> None:
        for row in self.schedule_tree.get_children():
            self.schedule_tree.delete(row)
        for appointment in self.get_appointments():
            self.schedule_tree.insert(
                "",
                "end",
                values=(appointment["appointment_date"], appointment["patient_name"], appointment["doctor_name"]),
            )

    def save_schedule(self) -> None:
        patient_value = self.schedule_patient.get().strip()
        appointment_date = self.schedule_date.get().strip()
        doctor_name = self.schedule_doctor.get().strip()

        if not patient_value or not appointment_date or not doctor_name:
            messagebox.showerror("Required fields", "Please complete patient, date, and doctor details.")
            return
        try:
            datetime.strptime(appointment_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", "Enter the appointment date in YYYY-MM-DD format.")
            return

        patient_id = int(patient_value.split(" - ")[0])
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO appointments (patient_id, doctor_name, appointment_date) VALUES (?, ?, ?)",
                (patient_id, doctor_name, appointment_date),
            )
            conn.commit()
        finally:
            conn.close()

        self.schedule_doctor.delete(0, tk.END)
        self.refresh_all()
        messagebox.showinfo("Saved", "Medication schedule saved successfully.")
