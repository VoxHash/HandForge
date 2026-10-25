package dev.voxhash.handforge.companion

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import com.google.android.material.button.MaterialButton
import java.io.File
import java.util.concurrent.Executors

/**
 * On-device / on-headset encode: SAF pick → stage under Download/HandForge →
 * Termux ffmpeg or bundled libffmpeg.so.
 *
 * On Meta Quest (Android), the same activity is the supported heavy-encode path.
 * Pass [EXTRA_PRESET_TIER]=heavy from Quest UI / JS bridge to emphasize capture presets.
 */
class LocalEncodeActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_PRESET_TIER = "preset_tier"
        const val EXTRA_HEAVY_FIRST = "heavy_first"
    }

    private val io = Executors.newSingleThreadExecutor()
    private lateinit var backendStatus: TextView
    private lateinit var thermalNote: TextView
    private lateinit var inputLabel: TextView
    private lateinit var encodeStatus: TextView
    private lateinit var presetSpinner: Spinner
    private lateinit var encodeButton: MaterialButton
    private lateinit var titleView: TextView
    private lateinit var blurbView: TextView

    private var presets: List<EncodePreset> = emptyList()
    private var pickedUri: Uri? = null
    private var pickedDisplayName: String = ""
    private var onQuest: Boolean = false

    private val pickMedia = registerForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri == null) return@registerForActivityResult
        try {
            contentResolver.takePersistableUriPermission(
                uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION,
            )
        } catch (_: SecurityException) {
            // Non-persistable grant is fine for a single encode session.
        }
        pickedUri = uri
        pickedDisplayName = SharedMediaStaging.displayNameOf(this, uri)
        inputLabel.text = pickedDisplayName
        encodeStatus.text = getString(R.string.input_ready)
    }

    private val requestPerms = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) {
        refreshBackend()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_local_encode)

        onQuest = QuestHeadset.isQuestDevice()

        backendStatus = findViewById(R.id.backendStatus)
        thermalNote = findViewById(R.id.thermalNote)
        inputLabel = findViewById(R.id.inputLabel)
        encodeStatus = findViewById(R.id.encodeStatus)
        presetSpinner = findViewById(R.id.presetSpinner)
        encodeButton = findViewById(R.id.encodeButton)
        titleView = findViewById(R.id.encodeTitle)
        blurbView = findViewById(R.id.encodeBlurb)

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.root)) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.updatePadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }

        if (onQuest) {
            titleView.text = getString(R.string.local_encode_title_quest)
            blurbView.text = getString(R.string.local_encode_blurb_quest)
            thermalNote.visibility = View.VISIBLE
            thermalNote.text = getString(R.string.thermal_note_quest)
        } else {
            thermalNote.visibility = View.GONE
        }

        loadPresets()
        ensurePermissions()
        refreshBackend()

        findViewById<MaterialButton>(R.id.pickInputButton).setOnClickListener {
            pickMedia.launch(
                arrayOf(
                    "audio/*",
                    "video/*",
                    "application/octet-stream",
                ),
            )
        }
        findViewById<MaterialButton>(R.id.backRemoteButton).setOnClickListener {
            finish()
        }
        encodeButton.setOnClickListener { startEncode() }
    }

    private fun loadPresets() {
        val raw = assets.open("encode_presets.json").bufferedReader().use { it.readText() }
        val all = OnDeviceEncodeCommand.parsePresetsJson(raw)
        val tierExtra = intent.getStringExtra(EXTRA_PRESET_TIER)
            ?: if (onQuest) OnDeviceEncodeCommand.TIER_ALL else OnDeviceEncodeCommand.TIER_ALL
        val heavyFirst = intent.getBooleanExtra(EXTRA_HEAVY_FIRST, onQuest) ||
            tierExtra.equals(OnDeviceEncodeCommand.TIER_HEAVY, ignoreCase = true)
        presets = OnDeviceEncodeCommand.filterPresets(
            all,
            tierFilter = tierExtra,
            heavyFirst = heavyFirst || onQuest,
        )
        if (presets.isEmpty()) {
            presets = all
        }
        val labels = presets.map { it.label }
        presetSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            labels,
        )
        // Prefer first heavy preset when opened for on-headset heavy encodes.
        if (heavyFirst || onQuest) {
            val heavyIdx = presets.indexOfFirst {
                it.tier.equals(OnDeviceEncodeCommand.TIER_HEAVY, ignoreCase = true)
            }
            if (heavyIdx >= 0) {
                presetSpinner.setSelection(heavyIdx)
            }
        }
    }

    private fun ensurePermissions() {
        val needed = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= 33) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_AUDIO)
                != PackageManager.PERMISSION_GRANTED
            ) {
                needed.add(Manifest.permission.READ_MEDIA_AUDIO)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_VIDEO)
                != PackageManager.PERMISSION_GRANTED
            ) {
                needed.add(Manifest.permission.READ_MEDIA_VIDEO)
            }
        } else {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                needed.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            }
            if (Build.VERSION.SDK_INT <= 28 &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                needed.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
            }
        }
        if (TermuxFfmpeg.isTermuxInstalled(packageManager) &&
            ContextCompat.checkSelfPermission(this, "com.termux.permission.RUN_COMMAND")
            != PackageManager.PERMISSION_GRANTED
        ) {
            needed.add("com.termux.permission.RUN_COMMAND")
        }
        if (needed.isNotEmpty()) {
            requestPerms.launch(needed.toTypedArray())
        }
    }

    private fun refreshBackend() {
        when (TermuxFfmpeg.detectBackend(this)) {
            TermuxFfmpeg.Backend.BUNDLED -> {
                backendStatus.text = getString(R.string.backend_bundled)
                encodeButton.isEnabled = true
            }
            TermuxFfmpeg.Backend.TERMUX -> {
                backendStatus.text = getString(R.string.backend_termux)
                encodeButton.isEnabled = true
            }
            TermuxFfmpeg.Backend.NONE -> {
                backendStatus.text = getString(R.string.backend_none)
                encodeButton.isEnabled = false
            }
        }
    }

    private fun selectedPreset(): EncodePreset? {
        val idx = presetSpinner.selectedItemPosition
        if (idx < 0 || idx >= presets.size) return null
        return presets[idx]
    }

    private fun startEncode() {
        val uri = pickedUri
        val preset = selectedPreset()
        if (uri == null) {
            Toast.makeText(this, R.string.no_input, Toast.LENGTH_SHORT).show()
            return
        }
        if (preset == null) {
            Toast.makeText(this, R.string.preset_label, Toast.LENGTH_SHORT).show()
            return
        }
        encodeButton.isEnabled = false
        encodeStatus.text = getString(R.string.staging)
        io.execute {
            try {
                val inName = pickedDisplayName.ifBlank { "input.bin" }
                    .replace(Regex("[^A-Za-z0-9._-]+"), "_")
                val outName = OnDeviceEncodeCommand.outputNameFor(inName, preset)
                val staged = SharedMediaStaging.stageInputAndReserveOutput(
                    this,
                    uri,
                    inName,
                    outName,
                )
                runOnUiThread {
                    encodeStatus.text = getString(
                        R.string.staged_paths,
                        staged.inputAbsPath,
                        staged.outputAbsPath,
                    )
                }
                when (TermuxFfmpeg.detectBackend(this)) {
                    TermuxFfmpeg.Backend.BUNDLED -> runBundled(preset, staged)
                    TermuxFfmpeg.Backend.TERMUX -> runTermux(preset, staged)
                    TermuxFfmpeg.Backend.NONE -> {
                        runOnUiThread {
                            encodeStatus.text = getString(R.string.backend_none)
                            encodeButton.isEnabled = false
                        }
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    encodeStatus.text = e.message ?: e.toString()
                    encodeButton.isEnabled = true
                    Toast.makeText(this, encodeStatus.text, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun runTermux(preset: EncodePreset, staged: SharedMediaStaging.StagedPaths) {
        val intent = TermuxFfmpeg.buildTermuxIntent(
            inputPath = staged.inputAbsPath,
            outputPath = staged.outputAbsPath,
            presetArgs = preset.args,
            workDir = staged.workDir,
        )
        runOnUiThread {
            try {
                startService(intent)
                encodeStatus.text = getString(
                    R.string.termux_launched,
                    staged.outputAbsPath,
                )
            } catch (e: Exception) {
                encodeStatus.text = getString(R.string.termux_failed, e.message ?: e.toString())
            }
            encodeButton.isEnabled = true
        }
    }

    private fun runBundled(preset: EncodePreset, staged: SharedMediaStaging.StagedPaths) {
        val bin = TermuxFfmpeg.bundledFfmpegPath(this)
            ?: throw IllegalStateException("libffmpeg.so missing — run scripts/fetch-android-ffmpeg.sh before assemble")
        val libDir = TermuxFfmpeg.bundledLibraryDir(this)
            ?: throw IllegalStateException("nativeLibraryDir unavailable")
        val argv = OnDeviceEncodeCommand.buildArgv(
            preset,
            staged.inputAbsPath,
            staged.outputAbsPath,
            binaryPath = bin.absolutePath,
        )
        val pb = ProcessBuilder(argv)
            .directory(File(staged.workDir))
            .redirectErrorStream(true)
        // Shared libav* / libsw* shipped beside libffmpeg.so under jniLibs/<abi>/.
        pb.environment()["LD_LIBRARY_PATH"] = libDir
        val proc = pb.start()
        val log = proc.inputStream.bufferedReader().readText()
        val code = proc.waitFor()
        runOnUiThread {
            if (code == 0 && File(staged.outputAbsPath).isFile) {
                encodeStatus.text = getString(R.string.encode_ok, staged.outputAbsPath)
            } else {
                encodeStatus.text = getString(R.string.encode_fail, code, log.takeLast(800))
            }
            encodeButton.isEnabled = true
        }
    }

    override fun onResume() {
        super.onResume()
        refreshBackend()
    }

    override fun onDestroy() {
        io.shutdownNow()
        super.onDestroy()
    }
}
