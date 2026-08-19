"""Resume Formatter - converts any resume into a client's house format.

Runs fully offline. No API keys, no internet, no data leaves the machine.
"""

import os
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import clients, extract, parser
from core.export import PdfExportError, to_pdf
from core.model import Education, Job, ResumeData, SkillGroup

APP_TITLE = "Resume Formatter"
OPEN_TYPES = [
    ("Resumes", "*.pdf *.docx *.doc *.rtf *.txt"),
    ("PDF", "*.pdf"),
    ("Word", "*.docx *.doc"),
    ("All files", "*.*"),
]
PAD = 8


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1040x740")
        self.minsize(880, 600)

        self.data = ResumeData()
        self.source_path: Path | None = None
        self.job_rows: list[dict] = []

        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()
        self._set_status("Open a resume to begin.")

    # ---------- layout ----------

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(PAD, PAD, PAD, 0))
        bar.pack(fill="x")

        ttk.Button(bar, text="Open resume…", command=self.on_open).pack(side="left")
        ttk.Label(bar, text="  Client format:").pack(side="left")
        self.client_var = tk.StringVar(value=clients.names()[0])
        ttk.Combobox(
            bar, textvariable=self.client_var, values=clients.names(),
            state="readonly", width=18,
        ).pack(side="left", padx=(4, 0))

        self.export_btn = ttk.Button(
            bar, text="Export DOCX + PDF", command=self.on_export, state="disabled"
        )
        self.export_btn.pack(side="right")

        self.source_label = ttk.Label(bar, text="No file loaded", foreground="#666")
        self.source_label.pack(side="right", padx=PAD)

    def _build_tabs(self) -> None:
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        basics = ttk.Frame(self.tabs, padding=PAD)
        ttk.Label(basics, text="Candidate name (appears in the page header)").pack(anchor="w")
        self.name_var = tk.StringVar()
        ttk.Entry(basics, textvariable=self.name_var, font=("Segoe UI", 11)).pack(
            fill="x", pady=(2, PAD)
        )
        self.warning_label = ttk.Label(basics, text="", foreground="#a15c00", wraplength=900)
        self.warning_label.pack(anchor="w")
        self.tabs.add(basics, text="Name")

        self.summary_text = self._add_text_tab(
            "Summary", "One bullet per line."
        )
        self.skills_text = self._add_text_tab(
            "Skills", "One line per group, as  Category: value, value, value"
        )
        self._build_experience_tab()
        self.certs_text = self._add_text_tab(
            "Certifications", "One certification per line."
        )
        self.edu_text = self._add_text_tab(
            "Education", "One per line, as  Degree | Institution | Year"
        )

    def _add_text_tab(self, title: str, hint: str) -> tk.Text:
        frame = ttk.Frame(self.tabs, padding=PAD)
        ttk.Label(frame, text=hint, foreground="#666").pack(anchor="w", pady=(0, 4))
        wrapper = ttk.Frame(frame)
        wrapper.pack(fill="both", expand=True)
        text = tk.Text(wrapper, wrap="word", font=("Segoe UI", 10), undo=True)
        scroll = ttk.Scrollbar(wrapper, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        self.tabs.add(frame, text=title)
        return text

    def _build_experience_tab(self) -> None:
        frame = ttk.Frame(self.tabs, padding=PAD)
        top = ttk.Frame(frame)
        top.pack(fill="x", pady=(0, 4))
        ttk.Label(
            top, text="Most recent role first. One responsibility per line.",
            foreground="#666",
        ).pack(side="left")
        ttk.Button(top, text="+ Add role", command=lambda: self._add_job_row(Job())).pack(
            side="right"
        )

        canvas = tk.Canvas(frame, highlightthickness=0)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.jobs_frame = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=self.jobs_frame, anchor="nw")

        self.jobs_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: self._on_wheel(e, canvas))

        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self.jobs_canvas = canvas
        self.tabs.add(frame, text="Experience")

    def _on_wheel(self, event, canvas: tk.Canvas) -> None:
        if str(self.tabs.tab(self.tabs.select(), "text")) == "Experience":
            canvas.yview_scroll(int(-event.delta / 120), "units")

    def _build_statusbar(self) -> None:
        self.status = ttk.Label(self, anchor="w", padding=(PAD, 4))
        self.status.pack(fill="x", side="bottom")

    def _set_status(self, message: str) -> None:
        self.status.configure(text=message)
        self.update_idletasks()

    # ---------- job rows ----------

    def _add_job_row(self, job: Job) -> None:
        box = ttk.LabelFrame(self.jobs_frame, text=f"Role {len(self.job_rows) + 1}", padding=PAD)
        box.pack(fill="x", expand=True, pady=(0, PAD), padx=(0, PAD))

        fields: dict[str, tk.StringVar] = {}
        grid = ttk.Frame(box)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=3)
        grid.columnconfigure(3, weight=2)

        for col, (key, label, value) in enumerate((
            ("company", "Company", job.company),
            ("dates", "Dates", job.dates),
        )):
            var = tk.StringVar(value=value)
            fields[key] = var
            ttk.Label(grid, text=label).grid(row=0, column=col * 2, sticky="w", padx=(0, 4))
            ttk.Entry(grid, textvariable=var).grid(
                row=0, column=col * 2 + 1, sticky="ew", padx=(0, PAD)
            )

        for col, (key, label, value) in enumerate((
            ("title", "Job title", job.title),
            ("project", "Project", job.project),
        )):
            var = tk.StringVar(value=value)
            fields[key] = var
            ttk.Label(grid, text=label).grid(row=1, column=col * 2, sticky="w", padx=(0, 4), pady=(4, 0))
            ttk.Entry(grid, textvariable=var).grid(
                row=1, column=col * 2 + 1, sticky="ew", padx=(0, PAD), pady=(4, 0)
            )

        text = tk.Text(box, wrap="word", height=7, font=("Segoe UI", 10), undo=True)
        text.insert("1.0", "\n".join(job.bullets))
        text.pack(fill="x", expand=True, pady=(PAD, 0))

        row = {"frame": box, "fields": fields, "text": text}

        def remove() -> None:
            self.job_rows.remove(row)
            box.destroy()
            self._renumber_jobs()

        ttk.Button(box, text="Remove role", command=remove).pack(anchor="e", pady=(4, 0))
        self.job_rows.append(row)

    def _renumber_jobs(self) -> None:
        for i, row in enumerate(self.job_rows, 1):
            row["frame"].configure(text=f"Role {i}")

    def _clear_jobs(self) -> None:
        for row in self.job_rows:
            row["frame"].destroy()
        self.job_rows.clear()

    # ---------- data binding ----------

    def _populate(self, data: ResumeData) -> None:
        self.name_var.set(data.name)
        self._set_text(self.summary_text, "\n".join(data.summary))
        self._set_text(
            self.skills_text,
            "\n".join(f"{g.category}: {g.values}" if g.category else g.values
                      for g in data.skills),
        )
        self._set_text(self.certs_text, "\n".join(data.certifications))
        self._set_text(
            self.edu_text,
            "\n".join(" | ".join((e.degree, e.institution, e.year)) for e in data.education),
        )
        self._clear_jobs()
        for job in data.experience:
            self._add_job_row(job)

        if data.dropped_sections:
            self.warning_label.configure(
                text="Heads up - this format has no section for: "
                + ", ".join(data.dropped_sections)
                + ". That content was left out; add anything important to the Summary."
            )
        else:
            self.warning_label.configure(text="")

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    @staticmethod
    def _lines(widget: tk.Text) -> list[str]:
        return [ln.strip() for ln in widget.get("1.0", "end").splitlines() if ln.strip()]

    def _collect(self) -> ResumeData:
        data = ResumeData(name=self.name_var.get().strip())
        data.summary = self._lines(self.summary_text)

        for line in self._lines(self.skills_text):
            head, sep, tail = line.partition(":")
            if sep:
                data.skills.append(SkillGroup(head.strip(), tail.strip()))
            else:
                data.skills.append(SkillGroup("", line))

        for row in self.job_rows:
            job = Job(**{k: v.get().strip() for k, v in row["fields"].items()})
            job.bullets = self._lines(row["text"])
            if any((job.company, job.title, job.project, job.bullets)):
                data.experience.append(job)

        data.certifications = self._lines(self.certs_text)

        for line in self._lines(self.edu_text):
            parts = [p.strip() for p in line.split("|")]
            parts += [""] * (3 - len(parts))
            data.education.append(Education(parts[0], parts[1], parts[2]))

        return data

    # ---------- actions ----------

    def on_open(self) -> None:
        path = filedialog.askopenfilename(title="Choose a resume", filetypes=OPEN_TYPES)
        if not path:
            return
        self.source_path = Path(path)
        self._set_status(f"Reading {self.source_path.name} …")
        try:
            lines = extract.extract(path)
            fallback = self.source_path.stem.replace("_", " ").replace("-", " ")
            self.data = parser.parse(lines, fallback_name=fallback)
        except extract.UnsupportedFormat as exc:
            self._set_status("Could not read that file.")
            messagebox.showwarning("Unsupported file", str(exc))
            return
        except Exception:
            self._set_status("Could not read that file.")
            messagebox.showerror("Error reading file", traceback.format_exc(limit=3))
            return

        self._populate(self.data)
        self.source_label.configure(text=self.source_path.name, foreground="#000")
        self.export_btn.configure(state="normal")
        found = (
            f"{len(self.data.experience)} roles, {len(self.data.skills)} skill groups, "
            f"{len(self.data.summary)} summary points"
        )
        self._set_status(f"Loaded {found}. Review every tab before exporting.")

    def on_export(self) -> None:
        data = self._collect()
        if not data.name:
            messagebox.showwarning("Name required", "Enter the candidate's name first.")
            self.tabs.select(0)
            return

        client = self.client_var.get()
        safe = "".join(c for c in data.name if c.isalnum() or c in " _-").strip() or "Resume"
        target = filedialog.asksaveasfilename(
            title="Save formatted resume",
            defaultextension=".docx",
            initialfile=f"{safe} - {client}.docx",
            filetypes=[("Word document", "*.docx")],
        )
        if not target:
            return

        self.export_btn.configure(state="disabled")
        self._set_status("Building document …")
        threading.Thread(
            target=self._export_worker, args=(client, data, Path(target)), daemon=True
        ).start()

    def _export_worker(self, client: str, data: ResumeData, target: Path) -> None:
        try:
            docx_path = clients.render(client, data, target)
        except Exception:
            detail = traceback.format_exc(limit=4)
            self.after(0, lambda: self._export_failed(detail))
            return

        self.after(0, lambda: self._set_status("Converting to PDF …"))
        pdf_error = ""
        try:
            to_pdf(docx_path)
        except PdfExportError as exc:
            pdf_error = str(exc)
        except Exception as exc:
            pdf_error = str(exc)

        self.after(0, lambda: self._export_done(docx_path, pdf_error))

    def _export_done(self, docx_path: Path, pdf_error: str) -> None:
        self.export_btn.configure(state="normal")
        if pdf_error:
            self._set_status(f"Saved {docx_path.name} (PDF failed).")
            messagebox.showwarning("Saved, but PDF failed", pdf_error)
        else:
            self._set_status(f"Saved {docx_path.name} and {docx_path.stem}.pdf")
            messagebox.showinfo(
                "Done", f"Saved to:\n{docx_path.parent}\n\n"
                f"{docx_path.name}\n{docx_path.stem}.pdf"
            )
        try:
            os.startfile(docx_path.parent)
        except Exception:
            pass

    def _export_failed(self, detail: str) -> None:
        self.export_btn.configure(state="normal")
        self._set_status("Export failed.")
        messagebox.showerror("Export failed", detail)


def main() -> None:
    # A windowed PyInstaller build has no stdout; anything that writes to it
    # (warnings, library progress bars) would otherwise raise.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    App().mainloop()


if __name__ == "__main__":
    main()
