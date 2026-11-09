"""SID2MIDI Accessible: wxPython frontend to sid2midi-public CLI."""
import os
import queue
import struct
import subprocess
import sys
import threading
from pathlib import Path
import wx


def parse_header(path):
    with open(path, 'rb') as handle:
        data = handle.read(0x76)
    if len(data) < 0x16 or data[:4] not in (b'PSID', b'RSID'):
        raise ValueError('Il file non ha un header PSID/RSID valido.')
    count = struct.unpack_from('>H', data, 0x0e)[0]
    start = struct.unpack_from('>H', data, 0x10)[0]
    if not 1 <= count <= 65535:
        raise ValueError('Numero di subtune non valido.')
    if not 1 <= start <= count:
        start = 1
    def field(offset):
        return data[offset:offset+32].split(b'\0', 1)[0].decode('latin-1', errors='replace').strip()
    return count, start, field(0x16), field(0x36), field(0x56)


def engine_path():
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    name = 'SID2MIDI-Engine.exe' if os.name == 'nt' else 'SID2MIDI-Engine'
    return base / name


class Main(wx.Frame):
    def __init__(self):
        super().__init__(None, title='SID2MIDI Accessible 0.1', size=(720, 580))
        self.messages = queue.Queue()
        self.running = False
        self.proc = None
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(0, 2, 8, 10)
        form.AddGrowableCol(1, 1)
        self.source = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.open_btn = wx.Button(panel, label='Apri file SID...')
        self.open_btn.Bind(wx.EVT_BUTTON, self.open_file)
        form.Add(self.open_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.source, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label='Informazioni del brano:'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.info = wx.StaticText(panel, label='Nessun file selezionato')
        form.Add(self.info, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label='Subtune:'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.song = wx.SpinCtrl(panel, min=1, max=1, initial=1)
        form.Add(self.song, 0, wx.EXPAND)
        self.all_songs = wx.CheckBox(panel, label='Converti tutte le subtune in file MIDI separati')
        self.all_songs.Bind(wx.EVT_CHECKBOX, self.toggle_all)
        form.AddSpacer(1)
        form.Add(self.all_songs, 0, wx.EXPAND)
        form.Add(wx.StaticText(panel, label='Durata massima (secondi):'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.seconds = wx.SpinCtrl(panel, min=1, max=3600, initial=180)
        form.Add(self.seconds, 0, wx.EXPAND)
        self.auto = wx.CheckBox(panel, label='Rileva automaticamente il loop (--auto)')
        form.AddSpacer(1)
        form.Add(self.auto, 0, wx.EXPAND)
        form.Add(wx.StaticText(panel, label='Tempo griglia MIDI (BPM):'), 0, wx.ALIGN_CENTER_VERTICAL)
        self.bpm = wx.SpinCtrl(panel, min=20, max=300, initial=125)
        form.Add(self.bpm, 0, wx.EXPAND)
        self.output_btn = wx.Button(panel, label='Scegli cartella di destinazione...')
        self.output_btn.Bind(wx.EVT_BUTTON, self.choose_dir)
        form.Add(self.output_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        self.output = wx.TextCtrl(panel, style=wx.TE_READONLY)
        form.Add(self.output, 1, wx.EXPAND)
        root.Add(form, 0, wx.EXPAND | wx.ALL, 14)
        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.convert_btn = wx.Button(panel, label='Converti in MIDI')
        self.convert_btn.Bind(wx.EVT_BUTTON, self.convert)
        self.cancel_btn = wx.Button(panel, label='Interrompi')
        self.cancel_btn.Disable()
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.cancel)
        actions.Add(self.convert_btn, 0, wx.RIGHT, 10)
        actions.Add(self.cancel_btn)
        root.Add(actions, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        self.status = wx.StaticText(panel, label='Pronto')
        root.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        root.Add(wx.StaticText(panel, label='Registro conversione:'), 0, wx.LEFT | wx.RIGHT, 14)
        self.log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        root.Add(self.log, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        panel.SetSizer(root)
        self.open_btn.SetFocus()
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def open_file(self, _):
        with wx.FileDialog(self, 'Apri file SID', wildcard='SID e MUS (*.sid;*.mus)|*.sid;*.mus|Tutti i file (*.*)|*.*', style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()
        try:
            count, start, title, author, copyright_ = parse_header(path)
            details = f'{title or Path(path).stem}; autore: {author or "sconosciuto"}; {count} subtune; predefinita: {start}'
            self.song.SetRange(1, count)
            self.song.SetValue(start)
            self.info.SetLabel(details)
        except ValueError as exc:
            # MUS files have no PSID header; CLI supports them but no reliable subtune count here.
            if Path(path).suffix.lower() == '.mus':
                self.song.SetRange(1, 1)
                self.song.SetValue(1)
                self.info.SetLabel('File MUS; una subtune selezionabile')
            else:
                wx.MessageBox(str(exc), 'File non valido', wx.OK | wx.ICON_ERROR, self)
                return
        self.source.SetValue(path)
        self.output.SetValue(str(Path(path).parent))
        self.status.SetLabel('File caricato. Seleziona una subtune e premi Converti in MIDI.')
        self.song.SetFocus()

    def toggle_all(self, _):
        self.song.Enable(not self.all_songs.GetValue())

    def choose_dir(self, _):
        with wx.DirDialog(self, 'Scegli cartella di destinazione', defaultPath=self.output.GetValue() or str(Path.home())) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.output.SetValue(dlg.GetPath())

    def convert(self, _):
        source = self.source.GetValue()
        out_dir = self.output.GetValue()
        if not source or not Path(source).is_file():
            wx.MessageBox('Apri prima un file SID.', 'SID2MIDI', wx.OK | wx.ICON_INFORMATION, self)
            return
        if not out_dir or not Path(out_dir).is_dir():
            wx.MessageBox('Scegli una cartella di destinazione valida.', 'SID2MIDI', wx.OK | wx.ICON_ERROR, self)
            return
        engine = engine_path()
        if not engine.is_file():
            wx.MessageBox(f'Motore non trovato: {engine}\nEstrai entrambi i file EXE dalla distribuzione nella stessa cartella.', 'Motore mancante', wx.OK | wx.ICON_ERROR, self)
            return
        dest = str(Path(out_dir) / (Path(source).stem + '.mid'))
        cmd = [str(engine), source, '-o', dest, '--seconds', str(self.seconds.GetValue()), '--bpm', str(self.bpm.GetValue()), '--report']
        cmd += ['--all-songs'] if self.all_songs.GetValue() else ['--song', str(self.song.GetValue())]
        if self.auto.GetValue():
            cmd.append('--auto')
        self.log.Clear()
        self.log.AppendText('Conversione avviata.\n')
        self.running = True
        self.convert_btn.Disable()
        self.cancel_btn.Enable()
        self.status.SetLabel('Conversione in corso...')
        threading.Thread(target=self.worker, args=(cmd,), daemon=True).start()

    def worker(self, cmd):
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace', creationflags=flags, bufsize=1)
            for line in self.proc.stdout:
                wx.CallAfter(self.log.AppendText, line)
            ret = self.proc.wait()
            wx.CallAfter(self.finish, ret)
        except Exception as exc:
            wx.CallAfter(self.error, str(exc))
        finally:
            self.proc = None

    def finish(self, ret):
        self.running = False
        self.convert_btn.Enable()
        self.cancel_btn.Disable()
        msg = 'Conversione completata. Controlla la cartella di destinazione.' if ret == 0 else f'Conversione non riuscita (codice {ret}). Consulta il registro.'
        self.status.SetLabel(msg)
        wx.MessageBox(msg, 'SID2MIDI', wx.OK | (wx.ICON_INFORMATION if ret == 0 else wx.ICON_WARNING), self)

    def error(self, msg):
        self.log.AppendText('\nERRORE: ' + msg)
        self.finish(1)

    def cancel(self, _):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.status.SetLabel('Interruzione richiesta...')

    def on_close(self, event):
        if self.running and self.proc and self.proc.poll() is None:
            if wx.MessageBox('Interrompere la conversione e chiudere?', 'Conferma', wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
                event.Veto()
                return
            self.proc.terminate()
        event.Skip()


if __name__ == '__main__':
    app = wx.App(False)
    frame = Main()
    frame.Show()
    app.MainLoop()
