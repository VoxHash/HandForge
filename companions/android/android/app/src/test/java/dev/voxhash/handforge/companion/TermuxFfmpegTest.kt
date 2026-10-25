package dev.voxhash.handforge.companion

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TermuxFfmpegTest {

    @Test
    fun buildBundledArgvPutsBinaryFirst() {
        val argv = TermuxFfmpeg.buildBundledArgv(
            binaryPath = "/data/app/lib/arm64/libffmpeg.so",
            inputPath = "/storage/emulated/0/Download/HandForge/in.wav",
            outputPath = "/storage/emulated/0/Download/HandForge/out.mp3",
            presetArgs = listOf("-c:a", "libmp3lame", "-b:a", "192k"),
        )
        assertEquals("/data/app/lib/arm64/libffmpeg.so", argv[0])
        assertEquals("-y", argv[1])
        assertEquals("-hide_banner", argv[2])
        assertEquals("-i", argv[3])
        assertEquals("/storage/emulated/0/Download/HandForge/in.wav", argv[4])
        assertTrue(argv.contains("libmp3lame"))
        assertEquals("/storage/emulated/0/Download/HandForge/out.mp3", argv.last())
    }

    @Test
    fun termuxCommandExtrasMatchRunCommandContract() {
        val extras = TermuxFfmpeg.termuxCommandExtras(
            inputPath = "/sdcard/Download/HandForge/a.mkv",
            outputPath = "/sdcard/Download/HandForge/a_hf.mp4",
            presetArgs = listOf("-c:v", "libx264", "-crf", "23"),
            workDir = "/sdcard/Download/HandForge",
        )
        assertEquals(TermuxFfmpeg.FFMPEG_PREFIX_PATH, extras[TermuxFfmpeg.EXTRA_PATH])
        assertEquals("/sdcard/Download/HandForge", extras[TermuxFfmpeg.EXTRA_WORKDIR])
        assertEquals(false, extras[TermuxFfmpeg.EXTRA_BACKGROUND])
        @Suppress("UNCHECKED_CAST")
        val args = extras[TermuxFfmpeg.EXTRA_ARGS] as List<String>
        assertEquals("-y", args[0])
        assertEquals("-i", args[2])
        assertEquals("/sdcard/Download/HandForge/a.mkv", args[3])
        assertTrue(args.contains("libx264"))
        assertEquals("/sdcard/Download/HandForge/a_hf.mp4", args.last())
        assertFalse(args[0].startsWith("/"))
    }
}
