package dev.voxhash.handforge.companion

import org.json.JSONObject

/**
 * Builds real FFmpeg argv lists for on-device encodes (Termux or bundled libffmpeg.so).
 * Preset definitions live in assets/encode_presets.json (shared with pytest).
 *
 * Tiers:
 * - `standard` — short phone/Quest jobs
 * - `heavy` — higher bitrate/resolution for Quest capture workflows (prefer short clips)
 */
data class EncodePreset(
    val id: String,
    val label: String,
    val extension: String,
    val args: List<String>,
    val tier: String = "standard",
)

object OnDeviceEncodeCommand {

    const val TIER_STANDARD = "standard"
    const val TIER_HEAVY = "heavy"
    const val TIER_ALL = "all"

    fun parsePresetsJson(raw: String): List<EncodePreset> {
        val root = JSONObject(raw)
        val arr = root.getJSONArray("presets")
        val out = ArrayList<EncodePreset>(arr.length())
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val argsJson = o.getJSONArray("args")
            val args = ArrayList<String>(argsJson.length())
            for (j in 0 until argsJson.length()) {
                args.add(argsJson.getString(j))
            }
            out.add(
                EncodePreset(
                    id = o.getString("id"),
                    label = o.getString("label"),
                    extension = o.getString("extension"),
                    args = args,
                    tier = o.optString("tier", TIER_STANDARD).ifBlank { TIER_STANDARD },
                ),
            )
        }
        return out
    }

    /** Filter + order presets: heavy first when [tierFilter] is heavy or on a Quest default. */
    fun filterPresets(
        presets: List<EncodePreset>,
        tierFilter: String = TIER_ALL,
        heavyFirst: Boolean = false,
    ): List<EncodePreset> {
        val filtered = when (tierFilter.lowercase()) {
            TIER_HEAVY -> presets.filter { it.tier.equals(TIER_HEAVY, ignoreCase = true) }
            TIER_STANDARD -> presets.filter {
                !it.tier.equals(TIER_HEAVY, ignoreCase = true)
            }
            else -> presets
        }
        if (!heavyFirst) return filtered
        return filtered.sortedBy { if (it.tier.equals(TIER_HEAVY, ignoreCase = true)) 0 else 1 }
    }

    fun heavyPresetIds(presets: List<EncodePreset>): List<String> {
        return presets.filter { it.tier.equals(TIER_HEAVY, ignoreCase = true) }.map { it.id }
    }

    /**
     * Full argv for ProcessBuilder / Termux (executable path first when [includeBinary] is set).
     */
    fun buildArgv(
        preset: EncodePreset,
        inputPath: String,
        outputPath: String,
        binaryPath: String? = null,
    ): List<String> {
        val argv = ArrayList<String>()
        if (binaryPath != null) {
            argv.add(binaryPath)
        }
        argv.add("-y")
        argv.add("-hide_banner")
        argv.add("-i")
        argv.add(inputPath)
        argv.addAll(preset.args)
        argv.add(outputPath)
        return argv
    }

    fun outputNameFor(inputDisplayName: String, preset: EncodePreset): String {
        val base = inputDisplayName.substringBeforeLast('.', inputDisplayName)
            .ifBlank { "handforge_out" }
            .replace(Regex("[^A-Za-z0-9._-]+"), "_")
        return "${base}_hf.${preset.extension}"
    }
}
