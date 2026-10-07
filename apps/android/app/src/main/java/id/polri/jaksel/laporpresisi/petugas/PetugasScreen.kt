package id.polri.jaksel.laporpresisi.petugas

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.polri.jaksel.laporpresisi.R
import id.polri.jaksel.laporpresisi.ui.ErrorBox
import id.polri.jaksel.laporpresisi.ui.Hint
import id.polri.jaksel.laporpresisi.ui.InputField
import id.polri.jaksel.laporpresisi.ui.Panel
import id.polri.jaksel.laporpresisi.ui.PresisiColors
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import id.polri.jaksel.laporpresisi.ui.PrimaryButton
import id.polri.jaksel.laporpresisi.ui.ScreenHeader
import id.polri.jaksel.laporpresisi.ui.SecondaryButton
import id.polri.jaksel.laporpresisi.ui.SectionLabel

/** Nilai `kind` dari `GET /notifications` untuk antrean laporan warga. */
const val KIND_CITIZEN_REPORT = "CITIZEN_REPORT"

/**
 * Keadaan layar petugas. Dua wajah: masuk ([profile] `null`) dan antrean. Tampilan tidak
 * tahu apa-apa tentang token — [PetugasActivity] yang memegang sesi.
 */
data class PetugasState(
    val username: String = "",
    val password: String = "",
    val signingIn: Boolean = false,
    val loginError: String? = null,
    val profile: Api.Profile? = null,
    val feed: Api.Feed? = null,
    /** Pesan di bawah antrean: galat pemuatan atau kabar verifikasi; `null` = bunyi bawaan. */
    val note: String? = null,
    /** Kode laporan yang sedang diverifikasi; tombolnya dimatikan. */
    val verifying: Set<String> = emptySet(),
    val busy: Boolean = false,
    val version: String = "",
)

class PetugasActions(
    val onUsername: (String) -> Unit,
    val onPassword: (String) -> Unit,
    val onSignIn: () -> Unit,
    val onRefresh: () -> Unit,
    val onSignOut: () -> Unit,
    val onVerify: (String) -> Unit,
)

@Composable
fun PetugasScreen(state: PetugasState, actions: PetugasActions) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Box(Modifier.fillMaxSize()) {
            Column(
                Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(20.dp),
            ) {
                ScreenHeader(stringResource(R.string.app_name), stringResource(R.string.subtitle))
                if (state.profile == null) LoginForm(state, actions) else QueueBoard(state, actions)
                Text(
                    "${stringResource(R.string.version_label)} ${state.version}",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier
                        .padding(top = 24.dp)
                        .align(Alignment.CenterHorizontally),
                )
            }
            if (state.busy) {
                CircularProgressIndicator(
                    color = PresisiColors.Accent,
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .padding(top = 8.dp),
                )
            }
        }
    }
}

@Composable
private fun LoginForm(state: PetugasState, actions: PetugasActions) {
    Column(Modifier.padding(top = 18.dp)) {
        InputField(
            label = stringResource(R.string.username),
            value = state.username,
            onValueChange = actions.onUsername,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
        )
        InputField(
            label = stringResource(R.string.password),
            value = state.password,
            onValueChange = actions.onPassword,
            password = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
        )
        ErrorBox(state.loginError, Modifier.padding(top = 12.dp))
        PrimaryButton(
            text = stringResource(if (state.signingIn) R.string.signing_in else R.string.sign_in),
            onClick = actions.onSignIn,
            enabled = !state.signingIn,
            modifier = Modifier.padding(top = 16.dp),
        )
        Hint(stringResource(R.string.login_note), Modifier.padding(top = 12.dp))
    }
}

@Composable
private fun QueueBoard(state: PetugasState, actions: PetugasActions) {
    val profile = state.profile ?: return
    val feed = state.feed

    Column(Modifier.padding(top = 18.dp)) {
        Panel {
            Text(profile.name, style = MaterialTheme.typography.titleMedium, fontSize = 15.sp)
            Text(
                profile.role.uppercase(),
                fontSize = 10.sp,
                letterSpacing = 1.2.sp,
                color = PresisiColors.InkMuted,
                modifier = Modifier.padding(top = 2.dp),
            )
        }

        Row(
            Modifier
                .fillMaxWidth()
                .padding(top = 18.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SectionLabel(stringResource(R.string.queue_title), Modifier.weight(1f))
            if (feed != null) Count(feed.total, size = 14.sp)
        }

        when {
            feed == null -> Unit
            feed.queues.isEmpty() -> Panel(Modifier.padding(top = 8.dp)) {
                Text(stringResource(R.string.queue_empty), style = MaterialTheme.typography.bodyMedium, fontSize = 13.sp)
            }
            else -> for (queue in feed.queues) {
                QueueCard(queue, Modifier.padding(top = 8.dp))
                if (queue.kind == KIND_CITIZEN_REPORT) {
                    for (item in queue.items) {
                        ReportCard(
                            item,
                            verifying = item.code in state.verifying,
                            onVerify = { actions.onVerify(item.code) },
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    }
                }
            }
        }

        Hint(state.note ?: stringResource(R.string.queue_note), Modifier.padding(top = 10.dp))

        Spacer(Modifier.height(16.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton(stringResource(R.string.refresh), onClick = actions.onRefresh, fullWidth = false)
            SecondaryButton(stringResource(R.string.sign_out), onClick = actions.onSignOut, fullWidth = false)
        }
    }
}

/** Angka antrean: merah bila ada yang menunggu, pudar bila nol. */
@Composable
private fun Count(total: Int, size: TextUnit) {
    Text(
        total.toString(),
        fontFamily = FontFamily.Monospace,
        fontWeight = FontWeight.Bold,
        fontSize = size,
        color = if (total > 0) PresisiColors.Critical else PresisiColors.InkFaint,
    )
}

/** Satu antrean: judul, jumlah, tindakan yang diharapkan, dan isi ringkasnya. */
@Composable
private fun QueueCard(queue: Api.Queue, modifier: Modifier = Modifier) {
    Panel(modifier) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                queue.title,
                style = MaterialTheme.typography.titleMedium,
                fontSize = 14.sp,
                modifier = Modifier.weight(1f),
            )
            Count(queue.total, size = 16.sp)
        }
        Text(
            queue.action,
            style = MaterialTheme.typography.bodySmall,
            color = PresisiColors.InkMuted,
            modifier = Modifier.padding(top = 2.dp),
        )
        val body = when {
            // Antrean kosong tetap digambar: "nol peringatan menunggu" adalah kabar baik,
            // dan menghilangkan barisnya membuat pembaca tidak dapat membedakan "tidak
            // ada" dari "tidak diperiksa".
            queue.items.isEmpty() -> "Tidak ada yang menunggu."
            // Laporan warga digambar satu per satu di bawah, masing-masing dengan
            // tombolnya. Merangkumnya di sini akan menampilkan isi yang sama dua kali.
            queue.kind == KIND_CITIZEN_REPORT -> null
            else -> queue.items.joinToString("\n") { "• ${it.headline} — ${it.detail}" }
        }
        if (body != null) {
            Text(
                body,
                style = MaterialTheme.typography.bodyMedium,
                fontSize = 13.sp,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}

/**
 * Satu laporan warga yang dapat diverifikasi langsung dari ponsel. Dipisahkan dari
 * [QueueCard] karena keduanya memikul hal yang berbeda: yang itu merangkum satu antrean,
 * yang ini satu perkara yang dapat ditindak.
 */
@Composable
private fun ReportCard(
    item: Api.QueueItem,
    verifying: Boolean,
    onVerify: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Panel(modifier) {
        Text(item.code, fontFamily = FontFamily.Monospace, fontSize = 12.sp, color = PresisiColors.InkMuted)
        Text(item.headline, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 4.dp))
        Text(
            item.detail,
            style = MaterialTheme.typography.bodyMedium,
            fontSize = 13.sp,
            modifier = Modifier.padding(top = 4.dp),
        )
        SecondaryButton(
            text = stringResource(if (verifying) R.string.verifying else R.string.verify),
            onClick = onVerify,
            enabled = !verifying,
            fullWidth = false,
            modifier = Modifier.padding(top = 10.dp),
        )
    }
}

private val NO_ACTIONS = PetugasActions({}, {}, {}, {}, {}, {})

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 640)
@Composable
private fun LoginPreview() {
    PresisiTheme { PetugasScreen(PetugasState(loginError = "Sesi Anda berakhir.", version = "2.2.0"), NO_ACTIONS) }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 900)
@Composable
private fun QueuePreview() {
    PresisiTheme {
        PetugasScreen(
            PetugasState(
                profile = Api.Profile("Bripka Contoh", "Polsek", emptyList()),
                feed = Api.Feed(
                    role = "Polsek",
                    total = 3,
                    queues = listOf(
                        Api.Queue(
                            "WARNING", "Peringatan menunggu diterima", "Terima dan tindak lanjuti", 2,
                            listOf(Api.QueueItem("EW-0012", "CURANMOR · Tebet", "18:00-23:59 WIB")),
                        ),
                        Api.Queue(
                            KIND_CITIZEN_REPORT, "Laporan warga menunggu triase", "Verifikasi", 1,
                            listOf(Api.QueueItem("CR-2026-0042", "Pencurian · Tebet Timur", "Motor hilang di depan rumah.")),
                        ),
                    ),
                ),
                version = "2.2.0",
            ),
            NO_ACTIONS,
        )
    }
}
