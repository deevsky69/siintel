package id.polri.jaksel.laporpresisi.petugas

import java.io.InputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Server HTTP kecil di dalam test, dibangun langsung di atas [ServerSocket].
 *
 * Dipakai daripada memalsukan [Api] itu sendiri karena yang paling mungkin salah justru ada
 * di lapisan HTTP: header `Set-Cookie` yang tidak terbaca, header `Cookie` yang tidak
 * terkirim, `401` yang tidak dibedakan dari galat lain. Memalsukan lapisan itu berarti
 * menguji tiruan, bukan kode yang dipasang di ponsel.
 *
 * Ditulis dengan soket biasa, bukan `com.sun.net.httpserver`: unit test Android dikompilasi
 * terhadap `android.jar`, dan kelas `com.sun.*` tidak ada di sana. Yang diperlukan di sini
 * hanya HTTP/1.1 seadanya — satu permintaan per sambungan, lalu ditutup.
 */
class FakeServer : AutoCloseable {

    class Reply(val code: Int, val body: String, val headers: Map<String, String> = emptyMap())

    class Received(
        val method: String,
        val path: String,
        val headers: Map<String, List<String>>,
        val body: String,
    ) {
        fun header(name: String): String? = headers.entries
            .firstOrNull { it.key.equals(name, ignoreCase = true) }
            ?.value?.firstOrNull()
    }

    private val socket = ServerSocket(0, 0, InetAddress.getByName("127.0.0.1"))
    private val queues = mutableMapOf<String, MutableList<Reply>>()
    private val worker: Thread

    val received = CopyOnWriteArrayList<Received>()

    val base: String get() = "http://127.0.0.1:${socket.localPort}"

    init {
        worker = Thread {
            while (!socket.isClosed) {
                val client = try {
                    socket.accept()
                } catch (_: Exception) {
                    return@Thread
                }
                client.use(::serve)
            }
        }
        worker.isDaemon = true
        worker.start()
    }

    /**
     * Mendaftarkan jawaban untuk [path]. Bila diberi lebih dari satu, jawabannya dipakai
     * berurutan — itulah cara menguji "ditolak dulu, berhasil setelah token diperbarui".
     * Jawaban terakhir dipakai berulang untuk permintaan berikutnya.
     */
    fun on(path: String, vararg replies: Reply): FakeServer {
        synchronized(queues) { queues[path] = replies.toMutableList() }
        return this
    }

    fun requestsTo(path: String): List<Received> = received.filter { it.path == path }

    override fun close() {
        socket.close()
        worker.interrupt()
    }

    private fun serve(client: Socket) {
        val input = client.getInputStream()
        val requestLine = readLine(input) ?: return
        val parts = requestLine.split(' ')
        val method = parts.getOrElse(0) { "" }
        val path = parts.getOrElse(1) { "" }.substringBefore('?')

        val headers = mutableMapOf<String, MutableList<String>>()
        while (true) {
            val line = readLine(input)
            if (line.isNullOrEmpty()) break
            val name = line.substringBefore(':').trim()
            val value = line.substringAfter(':', "").trim()
            headers.getOrPut(name) { mutableListOf() } += value
        }

        // Dua bentuk badan permintaan, dan keduanya perlu.
        //
        // `Content-Length` dipakai permintaan JSON biasa. Unggahan berkas memakai
        // `Transfer-Encoding: chunked` karena klien mengalirkannya tanpa menumpuknya di
        // memori lebih dulu — video puluhan megabita pada ponsel lama akan menjatuhkan
        // aplikasinya. Server uji yang hanya membaca `Content-Length` menerima badan KOSONG
        // dari unggahan, lalu lulus dengan gembira tanpa memeriksa apa pun.
        val chunked = headers.entries
            .firstOrNull { it.key.equals("Transfer-Encoding", ignoreCase = true) }
            ?.value?.firstOrNull()?.contains("chunked", ignoreCase = true) == true
        val length = headers.entries
            .firstOrNull { it.key.equals("Content-Length", ignoreCase = true) }
            ?.value?.firstOrNull()?.toIntOrNull() ?: 0

        val body = if (chunked) readChunked(input) else {
            ByteArray(length).also { if (length > 0) readFully(input, it) }
        }

        received += Received(method, path, headers, String(body, Charsets.UTF_8))

        val reply = synchronized(queues) {
            val queue = queues[path] ?: return@synchronized Reply(404, """{"error":{"message":"tidak terdaftar"}}""")
            if (queue.size > 1) queue.removeAt(0) else queue.first()
        }

        val payload = reply.body.toByteArray(Charsets.UTF_8)
        val head = buildString {
            append("HTTP/1.1 ${reply.code} ${reason(reply.code)}\r\n")
            append("Content-Type: application/json\r\n")
            append("Content-Length: ${payload.size}\r\n")
            // Satu permintaan per sambungan: tanpa ini `HttpURLConnection` menahan
            // sambungannya dan test menggantung saat server ditutup.
            append("Connection: close\r\n")
            reply.headers.forEach { (name, value) -> append("$name: $value\r\n") }
            append("\r\n")
        }
        client.getOutputStream().apply {
            write(head.toByteArray(Charsets.ISO_8859_1))
            write(payload)
            flush()
        }
    }

    private fun readLine(input: InputStream): String? {
        val buffer = StringBuilder()
        while (true) {
            val byte = input.read()
            if (byte == -1) return if (buffer.isEmpty()) null else buffer.toString()
            if (byte == '\n'.code) return buffer.toString().removeSuffix("\r")
            buffer.append(byte.toChar())
        }
    }

    /** Membaca badan ber-`Transfer-Encoding: chunked` sampai potongan berukuran nol. */
    private fun readChunked(input: InputStream): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        while (true) {
            val header = readLine(input) ?: break
            val size = header.substringBefore(';').trim().toIntOrNull(16) ?: break
            if (size == 0) break
            val chunk = ByteArray(size)
            readFully(input, chunk)
            out.write(chunk)
            readLine(input) // CRLF penutup potongan
        }
        return out.toByteArray()
    }

    private fun readFully(input: InputStream, into: ByteArray) {
        var read = 0
        while (read < into.size) {
            val count = input.read(into, read, into.size - read)
            if (count == -1) break
            read += count
        }
    }

    private fun reason(code: Int): String = when (code) {
        200 -> "OK"
        201 -> "Created"
        400 -> "Bad Request"
        401 -> "Unauthorized"
        404 -> "Not Found"
        429 -> "Too Many Requests"
        503 -> "Service Unavailable"
        else -> "Status"
    }
}

/** Penyimpanan token di memori — pengganti [TokenStore] yang menuntut keystore perangkat. */
class FakeTokens(
    override var accessToken: String? = null,
    override var refreshToken: String? = null,
) : Tokens {
    override fun clear() {
        accessToken = null
        refreshToken = null
    }
}
