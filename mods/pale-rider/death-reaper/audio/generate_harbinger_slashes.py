"""Prepare Steven's supplied blade recordings for the Harbinger sound events."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import wave

import numpy as np


RATE = 48_000
AUDIO = Path(__file__).resolve().parent
ROOT = AUDIO.parent
OUTPUT = ROOT / 'pack/Common/Sounds/Weapons/Scythe/Harbinger'
BUNDLED_FFMPEG = ROOT.parent / 'ranger-snipers/audio/tools/ffmpeg-9.0.2-essentials_build/bin/ffmpeg.exe'
AUDITION = AUDIO / 'previews/Harbinger_Slash_Audition.wav'
PRIMARY_ACTIVE = 0.05772
Q_WINDUP = 1.0108
Q_ACTIVE = 0.0777


@dataclass(frozen=True)
class Clip:
    source: str
    stem: str
    trim_start: float
    trim_end: float
    peak_dbfs: float
    tempo: float = 1.0
    starts_in_q_windup: bool = False


CLIPS = (
    Clip('floraphonic-steel-blade-slice-1-188213.mp3', 'Slash_01', 0.112, 0.610, -8.0),
    Clip('floraphonic-metal-blade-slice-76-200891.mp3', 'Slash_02', 0.147, 0.660, -8.0),
    Clip('floraphonic-steel-blade-slice-2-188214.mp3', 'Slash_03', 0.082, 0.590, -8.0),
    Clip('voicebosch-the-ballad-of-blades-audio-logo-253770.mp3', 'Final_Tithe_01', 0.405, 2.640, -6.5,
         tempo=1.20, starts_in_q_windup=True),
)


def decode(ffmpeg: Path, path: Path, rate: int = RATE, filters: str = '') -> np.ndarray:
    command = [str(ffmpeg), '-v', 'error', '-i', str(path), '-map', '0:a:0']
    if filters:
        command.extend(['-af', filters])
    command.extend(['-ac', '1', '-ar', str(rate), '-f', 'f32le', 'pipe:1'])
    result = subprocess.run(command, capture_output=True, check=True)
    return np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)


def encode(ffmpeg: Path, samples: np.ndarray, path: Path) -> None:
    subprocess.run(
        [str(ffmpeg), '-v', 'error', '-y', '-f', 'f32le', '-ar', str(RATE), '-ac', '1',
         '-i', 'pipe:0', '-map_metadata', '-1', '-c:a', 'libvorbis', '-q:a', '7',
         '-fflags', '+bitexact', '-flags:a', '+bitexact', str(path)],
        input=samples.astype('<f4').tobytes(), check=True,
    )


def dbfs(value: float) -> float:
    return float(20 * np.log10(max(value, 1e-12)))


def prepare(ffmpeg: Path, path: Path, clip: Clip) -> np.ndarray:
    filters = (f'pan=mono|c0=0.5*c0+0.5*c1,atrim=start={clip.trim_start}:end={clip.trim_end},'
               'asetpts=PTS-STARTPTS')
    if clip.tempo != 1.0:
        filters += f',atempo={clip.tempo}'
    samples = decode(ffmpeg, path, filters=filters)
    if len(samples) < RATE // 10 or not np.isfinite(samples).all() or not np.any(samples):
        raise ValueError(f'Invalid source audio: {path.name}')
    fade_in = round(0.005 * RATE)
    fade_out = round(0.025 * RATE)
    samples[:fade_in] *= np.sin(np.linspace(0, np.pi / 2, fade_in)) ** 2
    samples[-fade_out:] *= np.cos(np.linspace(0, np.pi / 2, fade_out)) ** 2
    return samples * (10 ** (clip.peak_dbfs / 20) / np.max(np.abs(samples)))


def inspect(ffmpeg: Path, ffprobe: Path, path: Path, clip: Clip) -> tuple[np.ndarray, dict]:
    metadata = subprocess.run(
        [str(ffprobe), '-v', 'error', '-select_streams', 'a:0', '-show_entries',
         'stream=codec_name,sample_rate,channels,duration', '-of', 'json', str(path)],
        capture_output=True, text=True, check=True,
    )
    [stream] = json.loads(metadata.stdout)['streams']
    if (stream['codec_name'], int(stream['sample_rate']), stream['channels']) != ('vorbis', RATE, 1):
        raise ValueError(f'Wrong native format: {path.name}')
    duration = float(stream['duration'])
    samples = decode(ffmpeg, path)[:round(duration * RATE)]
    if not len(samples) or not np.isfinite(samples).all() or not np.any(samples):
        raise ValueError(f'Invalid decoded audio: {path.name}')
    true_peak = dbfs(np.max(np.abs(decode(ffmpeg, path, RATE * 4))))
    if true_peak > -4:
        raise ValueError(f'True peak headroom too low: {path.name} {true_peak:.2f} dBTP')
    window = round(0.010 * RATE)
    power = np.convolve(samples**2, np.ones(window) / window, mode='valid')
    peak_time = (int(np.argmax(power)) + window / 2) / RATE
    q_clip = clip.starts_in_q_windup
    active_end = round(PRIMARY_ACTIVE * RATE - window / 2)
    early_peak_db = dbfs(np.sqrt(power[:active_end].max() / power.max()))
    if q_clip:
        if not Q_WINDUP <= peak_time <= Q_WINDUP + Q_ACTIVE:
            raise ValueError(f'Ballad climax falls outside Q strike: {peak_time:.4f} seconds')
    elif early_peak_db < -6 or duration > 0.52:
        raise ValueError(f'Combo slice falls outside its swing: {path.name} {early_peak_db:.2f} dB, {duration:.3f} seconds')
    return samples, {
        'file': (OUTPUT / path.name).relative_to(ROOT / 'pack/Common').as_posix(),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'sourceFile': clip.source,
        'sourceTrimSeconds': [clip.trim_start, clip.trim_end],
        'tempo': clip.tempo,
        'cue': 'Committed Q windup' if q_clip else 'Regular active swing',
        'codec': stream['codec_name'],
        'channels': stream['channels'],
        'sampleRateHz': RATE,
        'containerDurationSeconds': round(duration, 6),
        'estimatedTruePeakDbtp': round(true_peak, 2),
        'energyPeak10msMilliseconds': round(peak_time * 1000, 2),
        'peakRelativeToStrikeMilliseconds': round((peak_time - (Q_WINDUP if q_clip else 0)) * 1000, 2),
        'firstStrikeWindowRmsBelowClipPeakDb': None if q_clip else round(-early_peak_db, 2),
    }


def write_audition(clips: list[np.ndarray]) -> None:
    positions = [round(seconds * RATE) for seconds in (0.10, 0.62, 1.14, 2.05)]
    output = np.zeros(positions[-1] + len(clips[-1]) + round(0.15 * RATE))
    for offset, samples, gain in zip(positions, clips, (-2, -2, -2, -1), strict=True):
        output[offset:offset + len(samples)] += samples * 10 ** (gain / 20)
    AUDITION.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(AUDITION), 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes(np.rint(output * 32767).astype('<i2').tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True, help='Directory containing the four supplied MP3s')
    parser.add_argument('--ffmpeg', type=Path, help='FFmpeg executable next to ffprobe')
    args = parser.parse_args()
    ffmpeg = args.ffmpeg or (BUNDLED_FFMPEG if BUNDLED_FFMPEG.is_file() else Path(shutil.which('ffmpeg') or 'ffmpeg'))
    ffmpeg = ffmpeg.resolve()
    ffprobe = ffmpeg.with_name(f'ffprobe{ffmpeg.suffix}')
    if not ffmpeg.is_file() or not ffprobe.is_file():
        parser.error('FFmpeg and ffprobe must be available in the same directory.')

    sources = [args.source_dir / clip.source for clip in CLIPS]
    for source in sources:
        if not source.is_file():
            parser.error(f'Supplied source not found: {source.name}')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    metrics, clips = [], []
    # Verify all four converted files before replacing the packaged sounds.
    with TemporaryDirectory(prefix='blade-import-', dir=AUDIO.resolve()) as temp_dir:
        staged = Path(temp_dir)
        for clip, source in zip(CLIPS, sources, strict=True):
            path = staged / f'{clip.stem}.ogg'
            encode(ffmpeg, prepare(ffmpeg, source, clip), path)
            samples, evidence = inspect(ffmpeg, ffprobe, path, clip)
            evidence['sourceSHA256'] = hashlib.sha256(source.read_bytes()).hexdigest()
            metrics.append(evidence)
            clips.append(samples)
        for clip in CLIPS:
            path = staged / f'{clip.stem}.ogg'
            path.replace(OUTPUT / path.name)
    write_audition(clips)
    report = {'passed': True, 'source': 'Four user-supplied MP3 recordings', 'clips': metrics}
    (AUDIO / 'slash-audio-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
