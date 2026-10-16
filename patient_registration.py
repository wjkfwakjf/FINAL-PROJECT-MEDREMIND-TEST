import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk


class PatientRegistrationFeature:
    def _create_tab_patient(self, notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=self.tabs[0])

        left = ttk.LabelFrame(frame, text="Register Patient", padding=12)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(left, text="Patient ID").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.patient_id = ttk.Entry(left, width=30)
        self.patient_id.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(left, text="Full name").grid(row=1, column=0, sticky="w", pady=4)
        self.patient_name = ttk.Entry(left, width=30)
        self.patient_name.grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(left, text="Age").grid(row=2, column=0, sticky="w", pady=4)
        self.patient_age = ttk.Entry(left, width=30)
        self.patient_age.grid(row=2, column=1, padx=5, pady=4)

        ttk.Label(left, text="Contact").grid(row=3, column=0, sticky="w", pady=4)
        self.patient_contact = ttk.Entry(left, width=30)
        self.patient_contact.grid(row=3, column=1, padx=5, pady=4)

        ttk.Label(left, text="Condition").grid(row=4, column=0, sticky="w", pady=4)
        self.patient_condition = ttk.Entry(left, width=30)
        self.patient_condition.grid(row=4, column=1, padx=5, pady=4)

        patient_actions = ttk.Frame(left)
        patient_actions.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(patient_actions, text="Register Patient", command=self.register_patient).pack(
            side="left", padx=3
        )
        ttk.Button(patient_actions, text="Update Selected", command=self.update_patient).pack(
            side="left", padx=3
        )
        ttk.Button(patient_actions, text="Delete Selected", command=self.delete_patient).pack(
            side="left", padx=3
        )
        ttk.Button(patient_actions, text="Clear Form", command=self.clear_patient_form).pack(
            side="left", padx=3
        )

        right = ttk.LabelFrame(frame, text="Registered Patients", padding=10)
        right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        cols = ("ID", "Name", "Age", "Contact", "Condition")
        self.patient_tree = ttk.Treeview(right, columns=cols, show="headings")
        for col in cols:
            self.patient_tree.heading(col, text=col)
            self.patient_tree.column(col, width=120, anchor="center")
        self.patient_tree.pack(fill="both", expand=True)
        self.patient_tree.bind("<<TreeviewSelect>>", self._select_patient)
        ttk.Button(
            right,
            text="Renumber Patients from 1",
            command=self.renumber_patients,
        ).pack(anchor="e", pady=(8, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

    def _refresh_patient_tree(self) -> None:
        for row in self.patient_tree.get_children():
            self.patient_tree.delete(row)
        for patient in self.get_patients():
            self.patient_tree.insert(
                "",
                "end",
                values=(patient["id"], patient["full_name"], patient["age"], patient["contact"], patient["condition"]),
            )

    def _select_patient(self, _event=None) -> None:
        selection = self.patient_tree.selection()
        if not selection:
            return

        values = self.patient_tree.item(selection[0], "values")
        self.selected_patient_id = int(values[0])
        self.patient_id.delete(0, tk.END)
        self.patient_id.insert(0, values[0])
        self.patient_name.delete(0, tk.END)
        self.patient_name.insert(0, values[1])
        self.patient_age.delete(0, tk.END)
        self.patient_age.insert(0, values[2] or "")
        self.patient_contact.delete(0, tk.END)
        self.patient_contact.insert(0, values[3] or "")
        self.patient_condition.delete(0, tk.END)
        self.patient_condition.insert(0, values[4] or "")

    def clear_patient_form(self) -> None:
        self.selected_patient_id = None
        if hasattr(self, "patient_tree"):
            for item in self.patient_tree.selection():
                self.patient_tree.selection_remove(item)
        self.patient_id.delete(0, tk.END)
        self.patient_name.delete(0, tk.END)
        self.patient_age.delete(0, tk.END)
        self.patient_contact.delete(0, tk.END)
        self.patient_condition.delete(0, tk.END)

    def register_patient(self) -> None:
        name = self.patient_name.get().strip()
        age_text = self.patient_age.get().strip()
        contact = self.patient_contact.get().strip()
        condition = self.patient_condition.get().strip()
        requested_id_text = self.patient_id.get().strip()

        if not name or not age_text or not contact:
            messagebox.showerror("Required fields", "Please enter patient name, age, and contact details.")
            return

        try:
            age = int(age_text)
            if age < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input", "Age must be a non-negative whole number.")
            return

        try:
            requested_id = self._parse_patient_id(requested_id_text, allow_blank=True)
            self._save_patient_record(
                None,
                requested_id,
                name,
                age,
                contact,
                condition or "General care",
            )
        except ValueError as exc:
            messagebox.showerror("Invalid patient ID", str(exc))
            return

        self.clear_patient_form()
        self.refresh_all()
        messagebox.showinfo("Success", "Patient registered successfully.")

    def update_patient(self) -> None:
        if self.selected_patient_id is None:
            messagebox.showinfo("Select patient", "Select a patient from the list before updating.")
            return

        name = self.patient_name.get().strip()
        age_text = self.patient_age.get().strip()
        contact = self.patient_contact.get().strip()
        condition = self.patient_condition.get().strip()
        requested_id_text = self.patient_id.get().strip()
        if not name or not age_text or not contact:
            messagebox.showerror("Required fields", "Please enter patient name, age, and contact details.")
            return

        try:
            age = int(age_text)
            if age < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input", "Age must be a non-negative whole number.")
            return

        try:
            requested_id = self._parse_patient_id(requested_id_text)
            if requested_id is None:
                raise ValueError("Patient ID is required when updating a patient.")
            self._save_patient_record(
                self.selected_patient_id,
                requested_id,
                name,
                age,
                contact,
                condition or "General care",
            )
        except ValueError as exc:
            messagebox.showerror("Invalid patient ID", str(exc))
            return

        self.clear_patient_form()
        self.refresh_all()
        messagebox.showinfo("Updated", "Patient details updated successfully.")

    @staticmethod
    def _parse_patient_id(value: str, allow_blank: bool = False) -> int | None:
        if not value and allow_blank:
            return None
        try:
            patient_id = int(value)
        except ValueError as exc:
            raise ValueError("Patient ID must be a positive whole number.") from exc
        if patient_id < 1:
            raise ValueError("Patient ID must be a positive whole number.")
        return patient_id

    def _save_patient_record(
        self,
        current_id: int | None,
        requested_id: int | None,
        name: str,
        age: int,
        contact: str,
        condition: str,
    ) -> int:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if current_id is None:
                if requested_id is None:
                    cursor = conn.execute(
                        """
                        INSERT INTO patients (full_name, age, contact, condition)
                        VALUES (?, ?, ?, ?)
                        """,
                        (name, age, contact, condition),
                    )
                else:
                    duplicate = conn.execute(
                        "SELECT 1 FROM patients WHERE id = ?",
                        (requested_id,),
                    ).fetchone()
                    if duplicate is not None:
                        raise ValueError(f"Patient ID {requested_id} is already in use.")
                    cursor = conn.execute(
                        """
                        INSERT INTO patients (id, full_name, age, contact, condition)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (requested_id, name, age, contact, condition),
                    )
                saved_id = int(cursor.lastrowid)
            else:
                if requested_id is None:
                    raise ValueError("Patient ID is required when updating a patient.")
                if requested_id != current_id:
                    duplicate = conn.execute(
                        "SELECT 1 FROM patients WHERE id = ?",
                        (requested_id,),
                    ).fetchone()
                    if duplicate is not None:
                        raise ValueError(f"Patient ID {requested_id} is already in use.")
                    for table in ("medicines", "appointments", "medication_history"):
                        conn.execute(
                            f"UPDATE {table} SET patient_id = ? WHERE patient_id = ?",
                            (requested_id, current_id),
                        )

                cursor = conn.execute(
                    """
                    UPDATE patients
                    SET id = ?, full_name = ?, age = ?, contact = ?, condition = ?
                    WHERE id = ?
                    """,
                    (
                        requested_id,
                        name,
                        age,
                        contact,
                        condition,
                        current_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError("The selected patient no longer exists.")
                saved_id = requested_id

            conn.execute(
                """
                UPDATE sqlite_sequence
                SET seq = MAX(seq, (SELECT COALESCE(MAX(id), 0) FROM patients))
                WHERE name = 'patients'
                """
            )
            conn.commit()
            return saved_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _renumber_patient_ids(self) -> dict[int, int]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            patients = conn.execute(
                "SELECT id FROM patients ORDER BY id"
            ).fetchall()
            sequence = conn.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = 'patients'"
            ).fetchone()
            highest_used_id = max(
                int(sequence["seq"]) if sequence is not None else 0,
                max((int(patient["id"]) for patient in patients), default=0),
            )
            temporary_start = highest_used_id + len(patients) + 1
            mappings = {
                int(patient["id"]): index
                for index, patient in enumerate(patients, start=1)
            }
            temporary_ids = {
                old_id: temporary_start + index
                for index, old_id in enumerate(mappings)
            }

            for old_id, temporary_id in temporary_ids.items():
                conn.execute(
                    "UPDATE patients SET id = ? WHERE id = ?",
                    (temporary_id, old_id),
                )
                for table in ("medicines", "appointments", "medication_history"):
                    conn.execute(
                        f"UPDATE {table} SET patient_id = ? WHERE patient_id = ?",
                        (temporary_id, old_id),
                    )

            for old_id, new_id in mappings.items():
                temporary_id = temporary_ids[old_id]
                conn.execute(
                    "UPDATE patients SET id = ? WHERE id = ?",
                    (new_id, temporary_id),
                )
                for table in ("medicines", "appointments", "medication_history"):
                    conn.execute(
                        f"UPDATE {table} SET patient_id = ? WHERE patient_id = ?",
                        (new_id, temporary_id),
                    )

            highest_used_id = max(highest_used_id, len(patients))
            if sequence is None:
                conn.execute(
                    "INSERT INTO sqlite_sequence (name, seq) VALUES ('patients', ?)",
                    (highest_used_id,),
                )
            else:
                conn.execute(
                    """
                    UPDATE sqlite_sequence
                    SET seq = ?
                    WHERE name = 'patients'
                    """,
                    (highest_used_id,),
                )
            conn.commit()
            return mappings
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def renumber_patients(self) -> None:
        if not messagebox.askyesno(
            "Renumber patients",
            "Reassign patient IDs in ascending order starting from 1? "
            "Linked medicines, appointments, and medication history will be updated. "
            "Future registrations will continue from the previous highest ID.",
        ):
            return
        try:
            mappings = self._renumber_patient_ids()
        except sqlite3.Error as exc:
            messagebox.showerror("Could not renumber patients", str(exc))
            return

        self.clear_patient_form()
        self.refresh_all()
        changed_count = sum(
            old_id != new_id for old_id, new_id in mappings.items()
        )
        messagebox.showinfo(
            "Patient IDs updated",
            f"Renumbered {changed_count} patient ID(s).",
        )

    def delete_patient(self) -> None:
        if self.selected_patient_id is None:
            messagebox.showinfo("Select patient", "Select a patient from the list before deleting.")
            return
        if not messagebox.askyesno(
            "Delete patient",
            "Delete this patient and their active medicines and appointments? "
            "Medication history will be preserved.",
        ):
            return

        conn = self._connect()
        try:
            conn.execute("DELETE FROM medicines WHERE patient_id = ?", (self.selected_patient_id,))
            conn.execute("DELETE FROM appointments WHERE patient_id = ?", (self.selected_patient_id,))
            conn.execute("DELETE FROM patients WHERE id = ?", (self.selected_patient_id,))
            conn.commit()
        finally:
            conn.close()

        self.clear_patient_form()
        self.refresh_all()
        messagebox.showinfo("Deleted", "Patient deleted. Their medication history was preserved.")
