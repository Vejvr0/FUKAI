/*
 * Okno inštalačky.
 */

using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Threading;
using System.Windows.Forms;

namespace Fukai
{
    internal sealed class SetupForm : Form
    {
        private static readonly Color Ink = ColorTranslator.FromHtml("#263449");
        private static readonly Color Heading = ColorTranslator.FromHtml("#1A365D");
        private static readonly Color LabelInk = ColorTranslator.FromHtml("#2A64B0");
        private static readonly Color Box = ColorTranslator.FromHtml("#F2F6FB");
        private static readonly Color BoxBorder = ColorTranslator.FromHtml("#DCE7F3");
        private static readonly Color Muted = ColorTranslator.FromHtml("#718096");
        private static readonly Color BandFrom = ColorTranslator.FromHtml("#10233F");
        private static readonly Color BandTo = ColorTranslator.FromHtml("#245A91");
        private static readonly Color BandLabel = ColorTranslator.FromHtml("#8EC5FF");
        private static readonly Color BandText = ColorTranslator.FromHtml("#D8E8F8");

        private readonly Manifest _manifest;
        private readonly Detection _detection;
        private readonly Payload _payload;
        private readonly string _target;

        private readonly Panel _welcome = new Panel();
        private readonly Panel _progress = new Panel();
        private readonly Panel _done = new Panel();
        private readonly Label _bandTitle = new Label();
        private readonly Label _bandSubtitle = new Label();
        private readonly Label _step = new Label();
        private readonly TextBox _detail = new TextBox();
        private readonly ProgressBar _bar = new ProgressBar();
        private readonly Label _doneTitle = new Label();
        private readonly Label _doneText = new Label();
        private readonly CheckBox _desktop = new CheckBox();
        private readonly CheckBox _launch = new CheckBox();
        private readonly Button _action = new Button();
        private readonly Button _close = new Button();

        private bool _installed;

        public SetupForm(Manifest manifest, Detection detection, Payload payload, string target)
        {
            _manifest = manifest;
            _detection = detection;
            _payload = payload;
            _target = target;

            Text = "Inštalácia FUKAI";
            ClientSize = new Size(640, 520);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.White;
            Font = new Font("Segoe UI", 9f);
            ForeColor = Ink;
            // Ikona z vlastného exe – payload je vnorený, súbor sa z neho vyťahovať nedá.
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); }
            catch (Exception) { }

            Controls.Add(Band());
            BuildWelcome();
            BuildProgress();
            BuildDone();
            Controls.Add(Footer());
            Controls.Add(_welcome);
            Controls.Add(_progress);
            Controls.Add(_done);
            Show(_welcome);
        }

        // --- hlavička -------------------------------------------------

        private Panel Band()
        {
            Panel band = new Panel();
            band.Dock = DockStyle.Top;
            band.Height = 108;
            band.Paint += (sender, e) =>
            {
                using (LinearGradientBrush brush = new LinearGradientBrush(
                    band.ClientRectangle, BandFrom, BandTo, 35f))
                    e.Graphics.FillRectangle(brush, band.ClientRectangle);
            };

            Label mark = new Label();
            mark.Text = "F U K A I";
            mark.Font = new Font("Segoe UI", 8f, FontStyle.Bold);
            mark.ForeColor = BandLabel;
            mark.BackColor = Color.Transparent;
            mark.SetBounds(28, 18, 200, 16);

            _bandTitle.Text = "Vitaj vo FUKAI";
            _bandTitle.Font = new Font("Segoe UI", 17f, FontStyle.Bold);
            _bandTitle.ForeColor = Color.White;
            _bandTitle.BackColor = Color.Transparent;
            _bandTitle.SetBounds(26, 38, 580, 32);

            _bandSubtitle.Text = "Lokálna AI konverzácia. Tvoje modely. Tvoje súkromie.";
            _bandSubtitle.ForeColor = BandText;
            _bandSubtitle.BackColor = Color.Transparent;
            _bandSubtitle.SetBounds(28, 74, 580, 20);

            band.Controls.Add(mark);
            band.Controls.Add(_bandTitle);
            band.Controls.Add(_bandSubtitle);
            return band;
        }

        // --- strana 1: uvítanie ---------------------------------------

        private void BuildWelcome()
        {
            Page(_welcome);
            int y = 16;

            if (_detection.Blocker != null)
            {
                _welcome.Controls.Add(Head("FUKAI sa na tomto počítači nedá nainštalovať", ref y));
                _welcome.Controls.Add(Paragraph(_detection.Blocker, ref y));
                return;
            }

            bool cuda = _detection.Backend == Backend.Cuda;
            _welcome.Controls.Add(Head("Čo sa stane", ref y));
            _welcome.Controls.Add(Paragraph(
                "Inštalácia stiahne Python a potrebné knižnice, vytvorí prostredie aplikácie " +
                "a overí, že funguje. Modely .gguf súčasťou nie sú, pridáš si ich v aplikácii.", ref y));

            List<string> hardware = new List<string>();
            if (cuda)
            {
                hardware.Add(_detection.GpuName + " · ovládač " + _detection.DriverVersion);
                hardware.Add("FUKAI bude počítať na grafickej karte (CUDA).");
            }
            else
            {
                hardware.Add("FUKAI bude počítať na procesore.");
                hardware.AddRange(_detection.Notes);
            }
            _welcome.Controls.Add(Group(cuda ? "GRAFICKÁ KARTA" : "VÝPOČTY", hardware.ToArray(), ref y));

            _welcome.Controls.Add(Group("INTERNET A MIESTO NA DISKU", new[]
            {
                "Inštalácia potrebuje pripojenie na internet.",
                "Stiahne približne " + (cuda ? "720 MB" : "130 MB") +
                    " a na disku zaberie približne " + (cuda ? "1,3 GB" : "0,4 GB") + "."
            }, ref y));

            _welcome.Controls.Add(Group("KAM SA INŠTALUJE", new[]
            {
                _target,
                "Chaty, nastavenia a modely sa ukladajú zvlášť do:",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "FUKAI")
            }, ref y));

            _desktop.Text = "Vytvoriť zástupcu na ploche";
            _desktop.Checked = true;
            _desktop.ForeColor = Ink;
            _desktop.SetBounds(2, y + 6, 300, 22);
            _welcome.Controls.Add(_desktop);
        }

        // --- strana 2: priebeh ----------------------------------------

        private void BuildProgress()
        {
            Page(_progress);
            _progress.Visible = false;

            _step.Text = "Pripravujem…";
            _step.Font = new Font("Segoe UI", 10f, FontStyle.Bold);
            _step.ForeColor = Heading;
            _step.SetBounds(2, 16, 580, 22);

            _bar.Style = ProgressBarStyle.Marquee;
            _bar.MarqueeAnimationSpeed = 30;
            _bar.SetBounds(2, 46, 584, 6);

            _detail.Multiline = true;
            _detail.ReadOnly = true;
            _detail.ScrollBars = ScrollBars.Vertical;
            _detail.BorderStyle = BorderStyle.FixedSingle;
            _detail.BackColor = Box;
            _detail.ForeColor = Muted;
            _detail.Font = new Font("Consolas", 8.25f);
            _detail.SetBounds(2, 70, 584, 190);

            _progress.Controls.Add(_step);
            _progress.Controls.Add(_bar);
            _progress.Controls.Add(_detail);
        }

        // --- strana 3: dokončenie --------------------------------------

        private void BuildDone()
        {
            Page(_done);
            _done.Visible = false;

            _doneTitle.Font = new Font("Segoe UI", 11f, FontStyle.Bold);
            _doneTitle.ForeColor = Heading;
            _doneTitle.SetBounds(2, 16, 584, 26);

            _doneText.ForeColor = Ink;
            _doneText.SetBounds(2, 48, 584, 160);

            _launch.Text = "Spustiť FUKAI";
            _launch.Checked = true;
            _launch.ForeColor = Ink;
            _launch.SetBounds(2, 220, 300, 22);

            _done.Controls.Add(_doneTitle);
            _done.Controls.Add(_doneText);
            _done.Controls.Add(_launch);
        }

        // --- spodná lišta ----------------------------------------------

        private Panel Footer()
        {
            Panel footer = new Panel();
            footer.Dock = DockStyle.Bottom;
            footer.Height = 56;
            footer.Width = ClientSize.Width;
            footer.BackColor = Color.White;

            _action.Text = _detection.Blocker == null ? "Inštalovať" : "Zavrieť";
            _action.SetBounds(footer.Width - 28 - 120, 12, 120, 30);
            _action.Click += OnAction;

            _close.Text = "Zrušiť";
            _close.SetBounds(footer.Width - 28 - 120 - 10 - 100, 12, 100, 30);
            _close.Visible = _detection.Blocker == null;
            _close.Click += (sender, e) => Close();

            footer.Controls.Add(_action);
            footer.Controls.Add(_close);
            AcceptButton = _action;
            CancelButton = _close;
            return footer;
        }

        private void OnAction(object sender, EventArgs e)
        {
            if (_detection.Blocker != null || _installed)
            {
                if (_installed && _launch.Checked)
                    Start(Path.Combine(_target, "FUKAI.exe"));
                Close();
                return;
            }
            Show(_progress);
            _action.Enabled = false;
            _close.Enabled = false;
            _bandTitle.Text = "Inštalujem FUKAI";
            _bandSubtitle.Text = "Môže to trvať niekoľko minút. Okno nezatváraj.";

            bool desktop = _desktop.Checked;
            Thread worker = new Thread(() => Work(desktop));
            worker.IsBackground = true;
            worker.Start();
        }

        private void Work(bool desktop)
        {
            Log log = new Log(Path.Combine(_target, "install.log"), Append);
            log.Write("Inštalácia FUKAI " + _manifest.AppVersion + " do " + _target);
            foreach (string note in _detection.Notes)
                log.Write("upozornenie: " + note);
            try
            {
                string backend = new Installer(_manifest, _target, _payload, log, desktop).Run(_detection.Backend);
                log.Write("Hotovo, backend " + backend);
                Done(backend, null);
            }
            catch (InstallException exc)
            {
                log.Write("CHYBA: " + exc.Message);
                Done(null, exc.Message);
            }
            catch (Exception exc)
            {
                log.Write("CHYBA: " + exc);
                Done(null, exc.Message);
            }
        }

        private void Append(string line)
        {
            if (IsDisposed)
                return;
            BeginInvoke((MethodInvoker)delegate
            {
                _detail.AppendText(line + Environment.NewLine);
                int space = line.IndexOf(' ', 11);
                _step.Text = space > 0 ? line.Substring(space + 1) : line;
            });
        }

        private void Done(string backend, string error)
        {
            if (IsDisposed)
                return;
            BeginInvoke((MethodInvoker)delegate
            {
                _bar.Style = ProgressBarStyle.Continuous;
                _bar.Value = _bar.Maximum;
                _installed = error == null;
                _launch.Visible = _installed;

                if (_installed)
                {
                    _bandTitle.Text = "Hotovo";
                    _bandSubtitle.Text = "FUKAI je pripravený.";
                    _doneTitle.Text = "FUKAI je nainštalovaný";
                    string text = backend == "cuda"
                        ? "Modely pobežia na grafickej karte " + _detection.GpuName + "."
                        : "Modely pobežia na procesore.";
                    if (_detection.Notes.Count > 0)
                        text += "\n\n" + string.Join("\n", _detection.Notes.ToArray());
                    text += "\n\nJazykové modely .gguf nie sú súčasťou inštalácie – pridáš si ich priamo v aplikácii.";
                    _doneText.Text = text;
                    _action.Text = "Dokončiť";
                }
                else
                {
                    _bandTitle.Text = "Inštalácia zlyhala";
                    _bandSubtitle.Text = "FUKAI nie je nainštalovaný.";
                    _doneTitle.Text = "Inštalácia sa nepodarila";
                    _doneText.Text = error + "\n\nPodrobnosti sú v súbore:\n" +
                                     Path.Combine(_target, "install.log");
                    _action.Text = "Zavrieť";
                }
                _close.Visible = false;
                _action.Enabled = true;
                Show(_done);
            });
        }

        private static void Start(string exe)
        {
            try { System.Diagnostics.Process.Start(exe); }
            catch (Exception) { }
        }

        // --- stavba strán ----------------------------------------------

        private void Page(Panel panel)
        {
            panel.SetBounds(28, 108, 584, 356);
            panel.BackColor = Color.White;
        }

        private void Show(Panel page)
        {
            _welcome.Visible = page == _welcome;
            _progress.Visible = page == _progress;
            _done.Visible = page == _done;
        }

        private Label Head(string text, ref int y)
        {
            Label label = new Label();
            label.Text = text;
            label.Font = new Font("Segoe UI", 10f, FontStyle.Bold);
            label.ForeColor = Heading;
            label.SetBounds(2, y, 580, 22);
            y += 24;
            return label;
        }

        private Label Paragraph(string text, ref int y)
        {
            Label label = Wrapped(text, 580);
            label.Location = new Point(2, y);
            y += label.Height + 12;
            return label;
        }

        private Label Wrapped(string text, int width)
        {
            text = text.Replace("\r\n", "\n").Replace("\n", Environment.NewLine);

            Label label = new Label();
            label.Font = Font;
            label.ForeColor = Ink;
            label.AutoSize = false;
            label.AutoEllipsis = true;
            label.Size = new Size(width, TextRenderer.MeasureText(
                text, Font, new Size(width, 0), TextFormatFlags.WordBreak).Height);
            label.Text = text;
            return label;
        }

        private Panel Group(string title, string[] lines, ref int y)
        {
            int line = Font.Height + 2;
            int height = 30 + lines.Length * line;

            Panel panel = new Panel();
            panel.SetBounds(2, y, 580, height);
            panel.BackColor = Box;
            panel.Paint += (sender, e) => ControlPaint.DrawBorder(
                e.Graphics, panel.ClientRectangle, BoxBorder, ButtonBorderStyle.Solid);

            Label caption = new Label();
            caption.Text = title;
            caption.Font = new Font("Segoe UI", 7.5f, FontStyle.Bold);
            caption.ForeColor = LabelInk;
            caption.SetBounds(12, 8, 540, 14);
            panel.Controls.Add(caption);

            for (int i = 0; i < lines.Length; i++)
            {
                Label body = new Label();
                body.Font = Font;
                body.ForeColor = Ink;
                body.AutoSize = false;
                body.AutoEllipsis = true;
                body.SetBounds(12, 24 + i * line, 556, line);
                body.Text = lines[i];
                panel.Controls.Add(body);
            }

            y += height + 12;
            return panel;
        }
    }
}
