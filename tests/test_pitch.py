"""Verify audible transposition and duration using a known synthetic tone."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pitch_demo" / "python"))
from pitch import shift_voice


class PitchTest(unittest.TestCase):
    def test_octave_preserves_duration_and_doubles_frequency(self):
        sr = 16000
        tone = (0.2 * np.sin(2 * np.pi * 440 * np.arange(sr) / sr)).astype(np.float32)
        shifted = shift_voice(tone, sr, 12)
        self.assertEqual(len(shifted), len(tone))
        self.assertTrue(np.all(np.isfinite(shifted)))
        middle = shifted[2048:-2048]
        spectrum = np.abs(np.fft.rfft(middle * np.hanning(len(middle))))
        frequency = np.fft.rfftfreq(len(middle), 1 / sr)[np.argmax(spectrum)]
        self.assertAlmostEqual(frequency, 880, delta=8)
        self.assertLessEqual(float(np.max(np.abs(shifted))), 0.901)

    def test_bypass_and_range(self):
        audio = np.zeros(16000, dtype=np.float32)
        np.testing.assert_array_equal(shift_voice(audio, 16000, 0), audio)
        for value in (-1, 13):
            with self.assertRaises(ValueError):
                shift_voice(audio, 16000, value)


if __name__ == "__main__":
    unittest.main()
