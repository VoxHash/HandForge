package dev.voxhash.handforge.companion

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.app.PendingIntent
import java.io.File

/**
 * Discovers FFmpeg for on-device encodes and launches Termux RUN_COMMAND when needed.
 *
 * Preferred path: Termux `pkg install ffmpeg` + `allow-external-apps=true` in termux.properties.
 * Optional path: package `libffmpeg.so` under jniLibs (named so PackageManager extracts it).
 */
object TermuxFfmpeg {

    const val TERMUX_PACKAGE = "com.termux"
    const val RUN_COMMAND_ACTION = "com.termux.RUN_COMMAND"
    const val RUN_COMMAND_SERVICE = "com.termux.app.RunCommandService"
    const val EXTRA_PATH = "com.termux.RUN_COMMAND_PATH"
    const val EXTRA_ARGS = "com.termux.RUN_COMMAND_ARGUMENTS"
    const val EXTRA_WORKDIR = "com.termux.RUN_COMMAND_WORKDIR"
    const val EXTRA_BACKGROUND = "com.termux.RUN_COMMAND_BACKGROUND"
    const val EXTRA_LABEL = "com.termux.RUN_COMMAND_LABEL"
    const val EXTRA_PENDING_INTENT = "com.termux.RUN_COMMAND_PENDING_INTENT"
    const val FFMPEG_PREFIX_PATH = "\$PREFIX/bin/ffmpeg"
    const val FFMPEG_ABS_PATH = "/data/data/com.termux/files/usr/bin/ffmpeg"

    fun isTermuxInstalled(pm: PackageManager): Boolean {
        return try {
            pm.getPackageInfo(TERMUX_PACKAGE, 0)
            true
        } catch (_: PackageManager.NameNotFoundException) {
            false
        }
    }

    /** Bundled native executable packaged as libffmpeg.so (optional). */
    fun bundledFfmpegPath(context: Context): File? {
        val dir = context.applicationInfo.nativeLibraryDir ?: return null
        val f = File(dir, "libffmpeg.so")
        return if (f.isFile && f.canExecute()) f else null
    }

    enum class Backend {
        TERMUX,
        BUNDLED,
        NONE,
    }

    fun detectBackend(context: Context): Backend {
        if (bundledFfmpegPath(context) != null) return Backend.BUNDLED
        if (isTermuxInstalled(context.packageManager)) return Backend.TERMUX
        return Backend.NONE
    }

    fun buildTermuxIntent(
        inputPath: String,
        outputPath: String,
        presetArgs: List<String>,
        workDir: String = "/storage/emulated/0/Download/HandForge",
        resultPendingIntent: PendingIntent? = null,
    ): Intent {
        val args = ArrayList<String>()
        args.add("-y")
        args.add("-hide_banner")
        args.add("-i")
        args.add(inputPath)
        args.addAll(presetArgs)
        args.add(outputPath)

        return Intent().apply {
            component = ComponentName(TERMUX_PACKAGE, RUN_COMMAND_SERVICE)
            action = RUN_COMMAND_ACTION
            putExtra(EXTRA_PATH, FFMPEG_PREFIX_PATH)
            putExtra(EXTRA_ARGS, args.toTypedArray())
            putExtra(EXTRA_WORKDIR, workDir)
            putExtra(EXTRA_BACKGROUND, false)
            putExtra(EXTRA_LABEL, "HandForge on-device encode")
            if (resultPendingIntent != null) {
                putExtra(EXTRA_PENDING_INTENT, resultPendingIntent)
            }
        }
    }
}
