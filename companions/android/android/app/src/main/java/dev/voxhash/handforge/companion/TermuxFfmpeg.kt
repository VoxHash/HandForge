package dev.voxhash.handforge.companion

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.app.PendingIntent
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream

/**
 * Discovers FFmpeg for on-device encodes and launches Termux RUN_COMMAND when needed.
 *
 * Preferred path when present: packaged `libffmpeg.so` (+ libav* deps) under jniLibs
 * (see `scripts/fetch-android-ffmpeg.sh`). Fallback: Termux `pkg install ffmpeg` +
 * `allow-external-apps=true` in termux.properties.
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
    const val BUNDLED_LIB_NAME = "libffmpeg.so"
    private const val PRIVATE_BIN_DIR = "bundled-ffmpeg"

    fun isTermuxInstalled(pm: PackageManager): Boolean {
        return try {
            pm.getPackageInfo(TERMUX_PACKAGE, 0)
            true
        } catch (_: PackageManager.NameNotFoundException) {
            false
        }
    }

    /** Raw path where PackageManager extracts `libffmpeg.so` (may need chmod / copy). */
    fun nativeBundledCandidate(context: Context): File? {
        val dir = context.applicationInfo.nativeLibraryDir ?: return null
        val f = File(dir, BUNDLED_LIB_NAME)
        return if (f.isFile) f else null
    }

    /**
     * Executable path for ProcessBuilder. Copies into app-private storage when the
     * extracted native lib is not marked executable (some devices / W^X layouts).
     */
    fun bundledFfmpegPath(context: Context): File? {
        val native = nativeBundledCandidate(context) ?: return null
        if (native.canExecute()) {
            return native
        }
        val destDir = File(context.filesDir, PRIVATE_BIN_DIR).apply { mkdirs() }
        val dest = File(destDir, BUNDLED_LIB_NAME)
        if (!dest.isFile || dest.length() != native.length() || dest.lastModified() < native.lastModified()) {
            FileInputStream(native).use { input ->
                FileOutputStream(dest).use { output -> input.copyTo(output) }
            }
        }
        dest.setReadable(true, true)
        dest.setExecutable(true, true)
        return if (dest.isFile && dest.canExecute()) dest else null
    }

    /** Directory containing libav* / libsw* companions for LD_LIBRARY_PATH. */
    fun bundledLibraryDir(context: Context): String? {
        return context.applicationInfo.nativeLibraryDir
    }

    enum class Backend {
        BUNDLED,
        TERMUX,
        NONE,
    }

    fun detectBackend(context: Context): Backend {
        if (bundledFfmpegPath(context) != null) return Backend.BUNDLED
        if (isTermuxInstalled(context.packageManager)) return Backend.TERMUX
        return Backend.NONE
    }

    /** Pure argv helper for unit tests / ProcessBuilder (binary path first). */
    fun buildBundledArgv(
        binaryPath: String,
        inputPath: String,
        outputPath: String,
        presetArgs: List<String>,
    ): List<String> {
        val argv = ArrayList<String>(6 + presetArgs.size)
        argv.add(binaryPath)
        argv.add("-y")
        argv.add("-hide_banner")
        argv.add("-i")
        argv.add(inputPath)
        argv.addAll(presetArgs)
        argv.add(outputPath)
        return argv
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

    /** Pure extras map for tests (no Android Intent required). */
    fun termuxCommandExtras(
        inputPath: String,
        outputPath: String,
        presetArgs: List<String>,
        workDir: String = "/storage/emulated/0/Download/HandForge",
    ): Map<String, Any> {
        val args = ArrayList<String>()
        args.add("-y")
        args.add("-hide_banner")
        args.add("-i")
        args.add(inputPath)
        args.addAll(presetArgs)
        args.add(outputPath)
        return mapOf(
            EXTRA_PATH to FFMPEG_PREFIX_PATH,
            EXTRA_ARGS to args,
            EXTRA_WORKDIR to workDir,
            EXTRA_BACKGROUND to false,
            EXTRA_LABEL to "HandForge on-device encode",
        )
    }
}
