package dev.voxhash.handforge.companion

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class OnDeviceEncodeCommandTest {

    private fun presetsJson(): String {
        val path = File(
            "../src/main/assets/encode_presets.json",
        )
        val fromModule = File("src/main/assets/encode_presets.json")
        val f = when {
            fromModule.isFile -> fromModule
            path.isFile -> path
            else -> error("encode_presets.json not found (cwd=${File(".").absolutePath})")
        }
        return f.readText()
    }

    @Test
    fun parsesCuratedPresets() {
        val presets = OnDeviceEncodeCommand.parsePresetsJson(presetsJson())
        assertTrue(presets.size >= 8)
        assertTrue(presets.any { it.id == "audio_mp3_192" })
        assertTrue(presets.any { it.id == "video_mp4_crf23" })
        assertTrue(presets.any { it.id == "video_mp4_quest_1080" && it.tier == "heavy" })
    }

    @Test
    fun filtersHeavyTier() {
        val presets = OnDeviceEncodeCommand.parsePresetsJson(presetsJson())
        val heavy = OnDeviceEncodeCommand.filterPresets(
            presets,
            tierFilter = OnDeviceEncodeCommand.TIER_HEAVY,
        )
        assertTrue(heavy.isNotEmpty())
        assertTrue(heavy.all { it.tier == "heavy" })
        val ordered = OnDeviceEncodeCommand.filterPresets(
            presets,
            tierFilter = OnDeviceEncodeCommand.TIER_ALL,
            heavyFirst = true,
        )
        assertEquals("heavy", ordered.first().tier)
        assertTrue(OnDeviceEncodeCommand.heavyPresetIds(presets).contains("video_mp4_quest_720_hq"))
    }

    @Test
    fun heavyVideoPresetsCapThreads() {
        val heavyVideo = OnDeviceEncodeCommand.parsePresetsJson(presetsJson())
            .filter { it.tier == "heavy" && it.id.startsWith("video_") }
        assertTrue(heavyVideo.isNotEmpty())
        for (p in heavyVideo) {
            assertTrue(p.args.contains("-threads"))
            val idx = p.args.indexOf("-threads")
            assertEquals("2", p.args[idx + 1])
        }
    }

    @Test
    fun buildsFfmpegArgv() {
        val preset = OnDeviceEncodeCommand.parsePresetsJson(presetsJson())
            .first { it.id == "audio_aac_128" }
        val argv = OnDeviceEncodeCommand.buildArgv(
            preset,
            "/tmp/in.wav",
            "/tmp/out.m4a",
            binaryPath = "/data/app/lib/libffmpeg.so",
        )
        assertEquals("/data/app/lib/libffmpeg.so", argv[0])
        assertEquals("-y", argv[1])
        assertEquals("-i", argv[3])
        assertEquals("/tmp/in.wav", argv[4])
        assertEquals("/tmp/out.m4a", argv.last())
        assertTrue(argv.contains("aac"))
    }

    @Test
    fun outputNameSanitizes() {
        val preset = EncodePreset("x", "X", "mp3", emptyList())
        assertEquals(
            "My_Track_hf.mp3",
            OnDeviceEncodeCommand.outputNameFor("My Track.wav", preset),
        )
        assertFalse(OnDeviceEncodeCommand.outputNameFor("a.wav", preset).contains(" "))
    }
}
