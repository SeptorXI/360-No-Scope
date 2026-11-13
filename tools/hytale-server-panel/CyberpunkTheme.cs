using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Windows.Forms;

internal static class CyberpunkTheme
{
    internal static readonly Color Background = Color.FromArgb(12, 11, 17);
    internal static readonly Color Surface = Color.FromArgb(24, 19, 29);
    internal static readonly Color Input = Color.FromArgb(15, 13, 21);
    internal static readonly Color Ink = Color.FromArgb(245, 238, 242);
    internal static readonly Color Muted = Color.FromArgb(184, 169, 187);
    internal static readonly Color Accent = Color.FromArgb(249, 238, 42);
    internal static readonly Color Cyan = Color.FromArgb(78, 234, 235);
    internal static readonly Color Warning = Color.FromArgb(255, 179, 93);
    internal static readonly Color Border = Color.FromArgb(122, 48, 69);
    internal static readonly Color Red = Color.FromArgb(255, 84, 115);
    internal static readonly Color RedSurface = Color.FromArgb(46, 21, 34);

    [DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr window, int attribute, ref int value, int size);

    internal static void StyleWindow(Form window)
    {
        window.BackColor = Background;
        window.ForeColor = Ink;
        window.HandleCreated += delegate {
            const int useImmersiveDarkMode = 20;
            const int captionColor = 35;
            const int textColor = 36;
            int enabled = 1;
            int caption = ColorTranslator.ToWin32(Background);
            int text = ColorTranslator.ToWin32(Ink);
            DwmSetWindowAttribute(window.Handle, useImmersiveDarkMode, ref enabled, sizeof(int));
            DwmSetWindowAttribute(window.Handle, captionColor, ref caption, sizeof(int));
            DwmSetWindowAttribute(window.Handle, textColor, ref text, sizeof(int));
        };
    }

    internal static Font BodyFont(float size = 10, FontStyle style = FontStyle.Regular)
    {
        return new Font("Segoe UI", size, style);
    }

    internal static Font HeadingFont(float size, FontStyle style = FontStyle.Bold)
    {
        return new Font("Bahnschrift", size, style);
    }

    internal static void StyleButton(Button button, bool primary = false)
    {
        button.BackColor = primary ? Accent : RedSurface;
        button.ForeColor = primary ? Background : Ink;
        button.FlatStyle = FlatStyle.Flat;
        button.UseVisualStyleBackColor = false;
        button.Cursor = Cursors.Hand;
        button.FlatAppearance.BorderColor = primary ? Accent : Border;
        button.FlatAppearance.MouseOverBackColor = primary ? Color.FromArgb(255, 251, 128) : Color.FromArgb(69, 29, 46);
        button.FlatAppearance.MouseDownBackColor = primary ? Color.FromArgb(209, 196, 32) : Color.FromArgb(91, 36, 56);
        button.EnabledChanged += delegate {
            button.BackColor = button.Enabled ? (primary ? Accent : RedSurface) : Input;
            button.FlatAppearance.BorderColor = button.Enabled && primary ? Accent : Border;
        };
        button.Paint += (sender, args) => {
            if (button.Enabled) return;
            Rectangle bounds = button.ClientRectangle;
            using (var fill = new SolidBrush(Input)) args.Graphics.FillRectangle(fill, bounds);
            using (var edge = new Pen(Border)) args.Graphics.DrawRectangle(edge, 0, 0, bounds.Width - 1, bounds.Height - 1);
            TextRenderer.DrawText(args.Graphics, button.Text, button.Font, Rectangle.Inflate(bounds, -3, -2), Muted,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPrefix);
        };
    }
}

internal sealed class CyberpunkCard : Panel
{
    private readonly Color rail;

    internal CyberpunkCard(Color rail)
    {
        this.rail = rail;
        Dock = DockStyle.Fill;
        BackColor = CyberpunkTheme.Surface;
        DoubleBuffered = true;
        ResizeRedraw = true;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        int right = ClientSize.Width - 1;
        int bottom = ClientSize.Height - 1;
        const int cut = 13;
        if (right < cut || bottom < cut) return;

        using (var cutout = new SolidBrush(CyberpunkTheme.Background))
            e.Graphics.FillPolygon(cutout, new[] { new Point(right, bottom - cut), new Point(right, bottom), new Point(right - cut, bottom) });
        using (var edge = new Pen(CyberpunkTheme.Border))
            e.Graphics.DrawPolygon(edge, new[] { new Point(0, 0), new Point(right, 0), new Point(right, bottom - cut), new Point(right - cut, bottom), new Point(0, bottom) });
        using (var highlight = new SolidBrush(rail))
            e.Graphics.FillRectangle(highlight, 0, 0, Math.Min(52, right), 3);
    }
}

internal sealed class CyberpunkBanner : Panel
{
    internal CyberpunkBanner()
    {
        Dock = DockStyle.Fill;
        Margin = Padding.Empty;
        DoubleBuffered = true;
        ResizeRedraw = true;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        int right = ClientSize.Width - 1;
        int bottom = ClientSize.Height - 12;
        if (right < 260 || bottom < 56) return;

        var zone = new Rectangle(right - 260, 0, 261, bottom);
        using (var tint = new LinearGradientBrush(zone, CyberpunkTheme.Background, CyberpunkTheme.RedSurface, LinearGradientMode.Horizontal))
            e.Graphics.FillPolygon(tint, new[] { new Point(right - 195, 0), new Point(right, 0), new Point(right, bottom), new Point(right - 260, bottom) });

        using (var edge = new Pen(CyberpunkTheme.Border))
        {
            e.Graphics.DrawLine(edge, 0, bottom, right, bottom);
            e.Graphics.DrawLines(edge, new[] { new Point(right - 267, bottom - 7), new Point(right - 221, 22), new Point(right - 188, 22), new Point(right - 175, 9), new Point(right - 127, 9) });
            e.Graphics.DrawLine(edge, right - 190, bottom - 10, right, bottom - 10);
        }
        using (var accent = new SolidBrush(CyberpunkTheme.Accent))
            e.Graphics.FillPolygon(accent, new[] { new Point(0, bottom - 2), new Point(102, bottom - 2), new Point(98, bottom + 2), new Point(0, bottom + 2) });
        using (var red = new SolidBrush(CyberpunkTheme.Red))
            e.Graphics.FillRectangle(red, right - 34, bottom - 1, 35, 2);
    }
}

internal sealed class CyberpunkTabs : TabControl
{
    private readonly Font tabFont = CyberpunkTheme.HeadingFont(10);

    internal CyberpunkTabs()
    {
        SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
        SizeMode = TabSizeMode.Fixed;
        ItemSize = new Size(139, 34);
        SelectedIndexChanged += delegate { Invalidate(); };
        GotFocus += delegate { Invalidate(); };
        LostFocus += delegate { Invalidate(); };
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        e.Graphics.Clear(CyberpunkTheme.Background);
        if (TabCount == 0) return;

        int divider = GetTabRect(0).Bottom;
        using (var edge = new Pen(CyberpunkTheme.Border))
            e.Graphics.DrawLine(edge, 0, divider, ClientSize.Width, divider);

        for (int index = 0; index < TabCount; index++)
        {
            Rectangle tab = GetTabRect(index);
            tab.Width -= 5;
            bool selected = index == SelectedIndex;
            Color foreground = selected ? CyberpunkTheme.Accent : CyberpunkTheme.Muted;
            using (var fill = new SolidBrush(selected ? CyberpunkTheme.RedSurface : CyberpunkTheme.Surface))
                e.Graphics.FillRectangle(fill, tab);
            using (var rule = new Pen(selected ? CyberpunkTheme.Accent : CyberpunkTheme.Border))
                e.Graphics.DrawLine(rule, tab.Left, tab.Bottom - 1, tab.Right - 1, tab.Bottom - 1);

            TextRenderer.DrawText(e.Graphics, String.Format("{0:00}  /  {1}", index + 1, TabPages[index].Text.ToUpperInvariant()),
                tabFont, tab, foreground, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPrefix);
            if (selected && Focused && ShowFocusCues)
                ControlPaint.DrawFocusRectangle(e.Graphics, Rectangle.Inflate(tab, -4, -4), foreground, CyberpunkTheme.RedSurface);
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) tabFont.Dispose();
        base.Dispose(disposing);
    }
}
