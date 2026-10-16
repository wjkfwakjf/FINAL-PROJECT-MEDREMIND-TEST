import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk


class DoctorAppointmentRecordsFeature:
    def _create_tab_records(self, notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=self.tabs[5])

        left = ttk.LabelFrame(frame, text="Doctor/Appointment Records", padding=12)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(left, text="Patient").grid(row=0, column=0, sticky="w", pady=4)
        self.record_patient = ttk.Combobox(left, state="readonly", width=28)
        self.record_patient.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(left, text="Doctor Name").grid(row=1, column=0, sticky="w", pady=4)
        self.record_doctor = ttk.Entry(left, width=30)
        self.record_doctor.grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(left, text="Date").grid(row=2, column=0, sticky="w", pady=4)
        self.record_date = ttk.Entry(left, width=30)
        self.record_date.insert(0, datetime.today().strftime("%Y-%m-%d"))
        self.record_date.grid(row=2, column=1, padx=5, pady=4)

        ttk.Button(left, text="Record Appointment", command=self.save_record).grid(row=3, column=0, columnspan=2, pady=10)

        right = ttk.LabelFrame(frame, text="Appointments", padding=10)
        right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        cols = ("ID", "Patient", "Doctor", "Date")
        self.record_tree = ttk.Treeview(right, columns=cols, show="headings")
        for col in cols:
            self.record_tree.heading(col, text=col)
            self.record_tree.column(col, width=150, anchor="center")
        self.record_tree.pack(fill="both", expand=True)

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

    def _refresh_record_tree(self) -> None:
        for row in self.record_tree.get_children():
            self.record_tree.delete(row)
        for visit in self.get_appointments():
            self.record_tree.insert(
                "",
                "end",
                values=(visit["id"], visit["patient_name"], visit["doctor_name"], visit["appointment_date"]),
            )

    def save_record(self) -> None:
        patient_value = self.record_patient.get().strip()
        doctor_name = self.record_doctor.get().strip()
        appointment_date = self.record_date.get().strip()

        if not patient_value or not doctor_name or not appointment_date:
            messagebox.showerror("Required fields", "Please complete all appointment record fields.")
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

        self.record_doctor.delete(0, tk.END)
        self.refresh_all()
        messagebox.showinfo("Saved", "Doctor appointment record saved.")
