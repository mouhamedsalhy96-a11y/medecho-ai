from django import forms


TRAINING_LEVEL_CHOICES = [
    ("medical_student", "Medical student"),
    ("foundation_doctor", "Foundation doctor / FY1-FY2"),
    ("doctor_in_training", "Doctor in training / SHO level"),
    ("nurse", "Nurse"),
    ("midwife", "Midwife"),
    ("physiotherapist", "Physiotherapist"),
    ("paramedic", "Paramedic"),
    ("pharmacist", "Pharmacist"),
    ("advanced_practitioner", "Advanced practitioner"),
    ("other_healthcare_professional", "Other healthcare professional"),
]


class NewClinicalCaseForm(forms.Form):
    SPECIALTY_CHOICES = [
        ("general_practice", "General Practice"),
        ("emergency_medicine", "Emergency Medicine"),
        ("cardiology", "Cardiology"),
        ("respiratory", "Respiratory"),
        ("gastroenterology", "Gastroenterology"),
        ("neurology", "Neurology"),
        ("endocrinology", "Endocrinology"),
        ("paediatrics", "Paediatrics"),
        ("obstetrics_gynaecology", "Obstetrics and Gynaecology"),
        ("psychiatry", "Psychiatry"),
        ("random", "Random"),
    ]

    # Keep the database field name as "difficulty" for now to avoid migrations.
    # User-facing language now treats this as the learner's professional level/stage.
    DIFFICULTY_CHOICES = TRAINING_LEVEL_CHOICES

    specialty = forms.ChoiceField(
        choices=SPECIALTY_CHOICES,
        label="Specialty",
        widget=forms.Select(
            attrs={
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400",
            }
        ),
    )

    difficulty = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        label="Training level",
        widget=forms.Select(
            attrs={
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400",
            }
        ),
    )


class DoctorMessageForm(forms.Form):
    message = forms.CharField(
        label="Your question",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400",
                "placeholder": "Ask the patient a focused history-taking question...",
            }
        ),
    )


class InvestigationOrderForm(forms.Form):
    INVESTIGATION_CHOICES = [
        ("fbc", "Full blood count"),
        ("ue", "Urea and electrolytes"),
        ("lft", "Liver function tests"),
        ("crp", "CRP"),
        ("troponin", "Troponin"),
        ("d_dimer", "D-dimer"),
        ("abg", "Arterial blood gas"),
        ("urinalysis", "Urinalysis"),
        ("ecg", "ECG"),
        ("chest_xray", "Chest X-ray"),
        ("ct_head", "CT head"),
        ("ctpa", "CTPA"),
        ("mri", "MRI"),
        ("ultrasound", "Ultrasound"),
    ]

    investigations = forms.MultipleChoiceField(
        choices=INVESTIGATION_CHOICES,
        required=False,
        label="Common investigations",
        widget=forms.CheckboxSelectMultiple,
    )

    custom_investigations = forms.CharField(
        required=False,
        label="Custom investigations",
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-purple-400",
                "placeholder": "Enter one custom investigation per line, e.g.\nCT chest with contrast\nCT abdomen and pelvis\nSerum lipase",
            }
        ),
    )

    clinical_reason = forms.CharField(
        required=False,
        label="Clinical reason",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-purple-400",
                "placeholder": "Why are you ordering these investigations?",
            }
        ),
    )

    generate_images = forms.BooleanField(
        required=False,
        label="Generate educational images for imaging-style investigations",
        widget=forms.CheckboxInput(
            attrs={
                "class": "rounded border-slate-700 bg-slate-950 text-purple-400 focus:ring-purple-400",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        selected_investigations = cleaned_data.get("investigations") or []
        custom_text = cleaned_data.get("custom_investigations") or ""
        custom_investigations_list = [
            line.strip()
            for line in custom_text.strip().splitlines()
            if line.strip()
        ]

        if not selected_investigations and not custom_investigations_list:
            raise forms.ValidationError(
                "Please select at least one common investigation or enter at least one custom investigation."
            )

        cleaned_data["custom_investigations_list"] = custom_investigations_list
        return cleaned_data


class ConsultationSubmissionForm(forms.Form):
    final_diagnosis = forms.CharField(
        label="Final diagnosis",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400",
                "placeholder": "What is your most likely diagnosis?",
            }
        ),
    )

    differentials = forms.CharField(
        label="Differential diagnoses",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400",
                "placeholder": "List your key differentials and why.",
            }
        ),
    )

    investigation_interpretation = forms.CharField(
        label="Investigation interpretation",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400",
                "placeholder": "Interpret relevant investigation results.",
            }
        ),
    )

    management_plan = forms.CharField(
        label="Management plan",
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400",
                "placeholder": "Immediate management, definitive treatment, escalation and follow-up.",
            }
        ),
    )

    safety_netting = forms.CharField(
        label="Safety-netting",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400",
                "placeholder": "What red flags and return advice would you give?",
            }
        ),
    )
