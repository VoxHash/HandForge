package dev.voxhash.handforge.companion

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import android.widget.TextView
import android.view.ViewGroup
import android.widget.ScrollView
import android.widget.LinearLayout

/**
 * GrapheneOS-friendly WebView shell for the HandForge companion API.
 * No Google Play Services. Loads the live LAN companion UI after a health probe.
 */
class MainActivity : AppCompatActivity() {

    private val io = Executors.newSingleThreadExecutor()
    private lateinit var connectPane: ScrollView
    private lateinit var webPane: LinearLayout
    private lateinit var webView: WebView
    private lateinit var statusText: TextView
    private lateinit var hostInput: TextInputEditText
    private lateinit var portInput: TextInputEditText
    private lateinit var tokenInput: TextInputEditText

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        connectPane = findViewById(R.id.connectPane)
        webPane = findViewById(R.id.webPane)
        webView = findViewById(R.id.webView)
        statusText = findViewById(R.id.statusText)
        hostInput = findViewById(R.id.hostInput)
        portInput = findViewById(R.id.portInput)
        tokenInput = findViewById(R.id.tokenInput)

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.root)) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.updatePadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }

        loadPrefs()
        setupWebView()

        findViewById<MaterialButton>(R.id.connectButton).setOnClickListener {
            connect("/")
        }
        findViewById<MaterialButton>(R.id.questButton).setOnClickListener {
            connect("/quest.html")
        }
        findViewById<MaterialButton>(R.id.backButton).setOnClickListener {
            showConnect()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.cacheMode = WebSettings.LOAD_DEFAULT
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        // Do not rely on Google Safe Browsing / Play services.
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                statusText.text = "Loading…"
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                statusText.text = url ?: ""
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?,
            ) {
                if (request?.isForMainFrame == true) {
                    Toast.makeText(
                        this@MainActivity,
                        error?.description ?: "Load failed",
                        Toast.LENGTH_LONG,
                    ).show()
                }
            }
        }
    }

    private fun connect(path: String) {
        val host = hostInput.text?.toString()?.trim().orEmpty()
        val port = portInput.text?.toString()?.trim().orEmpty().ifEmpty { "8765" }
        val token = tokenInput.text?.toString()?.trim().orEmpty()
        if (host.isEmpty()) {
            statusText.text = "Host required"
            return
        }
        val root = "http://$host:$port"
        savePrefs(host, port, token)
        statusText.text = "Probing $root/api/health …"
        io.execute {
            val ok = probeHealth(root)
            runOnUiThread {
                if (!ok) {
                    statusText.text =
                        "Cannot reach companion at $root. Start `handforge serve --lan` on the desktop."
                    return@runOnUiThread
                }
                val url = if (token.isEmpty()) {
                    "$root$path"
                } else {
                    "$root$path" + (if (path.contains("?")) "&" else "?") +
                        "token=" + java.net.URLEncoder.encode(token, "UTF-8")
                }
                showWeb()
                webView.loadUrl(url)
            }
        }
    }

    private fun probeHealth(root: String): Boolean {
        return try {
            val conn = (URL("$root/api/health").openConnection() as HttpURLConnection).apply {
                connectTimeout = 4000
                readTimeout = 4000
                requestMethod = "GET"
                instanceFollowRedirects = false
            }
            val code = conn.responseCode
            conn.disconnect()
            code in 200..299
        } catch (_: Exception) {
            false
        }
    }

    private fun showWeb() {
        connectPane.visibility = View.GONE
        webPane.visibility = View.VISIBLE
    }

    private fun showConnect() {
        webView.loadUrl("about:blank")
        webPane.visibility = View.GONE
        connectPane.visibility = View.VISIBLE
    }

    private fun prefs() = getSharedPreferences("handforge_companion", Context.MODE_PRIVATE)

    private fun loadPrefs() {
        val p = prefs()
        hostInput.setText(p.getString("host", ""))
        portInput.setText(p.getString("port", "8765"))
        tokenInput.setText(p.getString("token", ""))
    }

    private fun savePrefs(host: String, port: String, token: String) {
        prefs().edit()
            .putString("host", host)
            .putString("port", port)
            .putString("token", token)
            .apply()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webPane.visibility == View.VISIBLE && webView.canGoBack()) {
            webView.goBack()
            return
        }
        if (webPane.visibility == View.VISIBLE) {
            showConnect()
            return
        }
        @Suppress("DEPRECATION")
        super.onBackPressed()
    }

    override fun onDestroy() {
        (webView.parent as? ViewGroup)?.removeView(webView)
        webView.destroy()
        io.shutdownNow()
        super.onDestroy()
    }
}
