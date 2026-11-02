STYLESHEET = """
    QFrame#toast {
        background: #ffffff;
        border: 1px solid #c9d6e3;
        border-left: 4px solid #3d87b6;
        border-radius: 8px;
    }
    QFrame#toast[severity="warning"] { border-left-color: #e0a100; }
    QFrame#toast[severity="error"]   { border-left-color: #d64545; }

    QLabel#toastTitle   { font-weight: 600; color: #10243a; }
    QLabel#toastMessage { color: #10243a; }
    QLabel#toastHint    { color: #5a6b7b; }

    QPushButton#toastClose        { border: none; background: transparent; color: #5a6b7b; }
    QPushButton#toastClose:hover  { color: #10243a; }

    QProgressBar#toastTimeline        { border: none; background: #e6edf3; border-radius: 1px; }
    QProgressBar#toastTimeline::chunk { background: #3d87b6; border-radius: 1px; }
    QFrame#toast[severity="warning"] QProgressBar#toastTimeline::chunk { background: #e0a100; }
"""