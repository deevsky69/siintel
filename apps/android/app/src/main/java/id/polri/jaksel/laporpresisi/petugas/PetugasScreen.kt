package id.polri.jaksel.laporpresisi.petugas

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ExitToApp
import androidx.compose.material.icons.outlined.Build
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.DateRange
import androidx.compose.material.icons.outlined.Done
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Place
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Star
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.polri.jaksel.laporpresisi.R
import id.polri.jaksel.laporpresisi.ui.BrandHeader
import id.polri.jaksel.laporpresisi.ui.CountPill
import id.polri.jaksel.laporpresisi.ui.ErrorBox
import id.polri.jaksel.laporpresisi.ui.Hint
import id.polri.jaksel.laporpresisi.ui.InputField
import id.polri.jaksel.laporpresisi.ui.Panel
import id.polri.jaksel.laporpresisi.ui.PresisiColors
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import id.polri.jaksel.laporpresisi.ui.PrimaryButton
import id.polri.jaksel.laporpresisi.ui.ScreenScaffold
import id.polri.jaksel.laporpresisi.ui.SecondaryButton
import id.polri.jaksel.laporpresisi.ui.SectionLabel
import id.polri.jaksel.laporpresisi.ui.StatChip

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

/**
 * Rupa tiap peran di kepala layar: ikon dan satu kalimat tugas. Isinya mengikuti docs/12;
 * yang menentukan isi antrean tetap server, bukan tabel ini.
 */
private data class RoleLook(val icon: ImageVector, val tagline: Int)

private fun roleLook(role: String): RoleLook = when (role.lowercase()) {
    "pimpinan" -> RoleLook(Icons.Outlined.Star, R.string.role_pimpinan)
    "polsek" -> RoleLook(Icons.Outlined.Place, R.string.role_polsek)
    "fungsi" -> RoleLook(Icons.Outlined.Build, R.string.role_fungsi)
    "administrator" -> RoleLook(Icons.Outlined.Settings, R.string.role_admin)
    else -> RoleLook(Icons.Outlined.Person, R.string.role_admin)
}

/** Ikon dan nama pendek tiap jenis antrean, untuk kepingan ringkasan dan kartu. */
private fun kindIcon(kind: String): ImageVector = when (kind) {
    "WARNING" -> Icons.Outlined.Warning
    KIND_CITIZEN_REPORT -> Icons.Outlined.Edit
    "DECISION" -> Icons.Outlined.CheckCircle
    "PATROL_PLAN" -> Icons.Outlined.DateRange
    "OPERATION" -> Icons.Outlined.Build
    else -> Icons.Outlined.Info
}

private fun kindShortLabel(kind: String): String = when (kind) {
    "WARNING" -> "peringatan"
    KIND_CITIZEN_REPORT -> "laporan"
    "DECISION" -> "keputusan"
    "PATROL_PLAN" -> "rencana"
    "PREDICTION" -> "prediksi"
    "OPERATION" -> "operasi"
    else -> kind.lowercase()
}

@Composable
fun PetugasScreen(state: PetugasState, actions: PetugasActions) {
    ScreenScaffold(busy = state.busy) {
        BrandHeader(stringResource(R.string.app_name), stringResource(R.string.subtitle), compact = true)
        if (state.profile == null) LoginForm(state, actions) else QueueBoard(state, actions)
        Text(
            "${stringResource(R.string.version_label)} ${state.version}",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier
                .padding(top = 24.dp)
                .align(Alignment.CenterHorizontally),
        )
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
            icon = Icons.Outlined.Lock,
            modifier = Modifier.padding(top = 16.dp),
        )
        Hint(stringResource(R.string.login_note), Modifier.padding(top = 12.dp))
    }
}

@Composable
private fun QueueBoard(state: PetugasState, actions: PetugasActions) {
    val profile = state.profile ?: return
    val feed = state.feed
    val look = roleLook(profile.role)

    Column(Modifier.padding(top = 18.dp)) {
        // ----- siapa saya -----
        Panel {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(look.icon, contentDescription = null, tint = PresisiColors.Accent, modifier = Modifier.size(30.dp))
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(profile.name, style = MaterialTheme.typography.titleMedium, fontSize = 15.sp)
                    Text(
                        profile.role.uppercase(),
                        fontSize = 10.sp,
                        letterSpacing = 1.2.sp,
                        color = PresisiColors.Accent,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                }
                if (feed != null) CountPill(feed.total)
            }
            Text(
                stringResource(look.tagline),
                style = MaterialTheme.typography.bodySmall,
                color = PresisiColors.InkMuted,
                modifier = Modifier.padding(top = 10.dp),
            )
        }

        if (feed != null) {
            // ----- ringkasan satu baris -----
            if (feed.queues.isNotEmpty()) {
                SectionLabel(stringResource(R.string.queue_summary), Modifier.padding(top = 18.dp))
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    for (queue in feed.queues) {
                        StatChip(kindIcon(queue.kind), queue.total, kindShortLabel(queue.kind))
                    }
                }
            }

            // ----- antrean -----
            SectionLabel(stringResource(R.string.queue_title), Modifier.padding(top = 18.dp))
            when {
                feed.queues.isEmpty() -> Panel(Modifier.padding(top = 8.dp)) {
                    Text(stringResource(R.string.queue_empty), style = MaterialTheme.typography.bodyMedium, fontSize = 13.sp)
                }
                feed.total == 0 -> Panel(Modifier.padding(top = 8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = PresisiColors.Ok, modifier = Modifier.size(22.dp))
                        Spacer(Modifier.width(10.dp))
                        Text(stringResource(R.string.queue_all_clear), style = MaterialTheme.typography.bodyMedium)
                    }
                }
                else -> for (queue in feed.queues) {
                    // Antrean nol tetap ada di ringkasan atas; kartunya tidak perlu diulang.
                    if (queue.total == 0) continue
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
        }

        Hint(state.note ?: stringResource(R.string.queue_note), Modifier.padding(top = 10.dp))

        Spacer(Modifier.height(16.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton(stringResource(R.string.refresh), onClick = actions.onRefresh, fullWidth = false, icon = Icons.Outlined.Refresh)
            SecondaryButton(stringResource(R.string.sign_out), onClick = actions.onSignOut, fullWidth = false, icon = Icons.AutoMirrored.Outlined.ExitToApp)
        }
    }
}

/** Satu antrean: ikon jenis, judul, jumlah, tindakan yang diharapkan, dan isi ringkasnya. */
@Composable
private fun QueueCard(queue: Api.Queue, modifier: Modifier = Modifier) {
    Panel(modifier) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(kindIcon(queue.kind), contentDescription = null, tint = PresisiColors.Accent, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(queue.title, style = MaterialTheme.typography.titleMedium, fontSize = 14.sp)
                Text(queue.action, style = MaterialTheme.typography.bodySmall, color = PresisiColors.InkMuted)
            }
            CountPill(queue.total, Modifier.padding(start = 8.dp))
        }
        // Laporan warga digambar satu per satu di bawah, masing-masing dengan tombolnya.
        // Merangkumnya di sini akan menampilkan isi yang sama dua kali.
        if (queue.kind != KIND_CITIZEN_REPORT && queue.items.isNotEmpty()) {
            Column(Modifier.padding(top = 10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                for (item in queue.items) {
                    Row(verticalAlignment = Alignment.Top) {
                        Text("•", color = PresisiColors.InkFaint, modifier = Modifier.width(14.dp))
                        Column {
                            Text(item.headline, style = MaterialTheme.typography.bodyLarge, fontSize = 13.sp)
                            if (item.detail.isNotBlank()) {
                                Text(item.detail, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
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
    Panel(modifier, borderColor = PresisiColors.Accent.copy(alpha = 0.35f)) {
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
            icon = Icons.Outlined.Done,
            modifier = Modifier.padding(top = 10.dp),
        )
    }
}

private val NO_ACTIONS = PetugasActions({}, {}, {}, {}, {}, {})

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 640)
@Composable
private fun LoginPreview() {
    PresisiTheme { PetugasScreen(PetugasState(loginError = "Sesi Anda berakhir.", version = "2.3.0"), NO_ACTIONS) }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 960)
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
                        Api.Queue("OPERATION", "Tindakan menunggu hasil", "Catat hasil", 0, emptyList()),
                    ),
                ),
                version = "2.3.0",
            ),
            NO_ACTIONS,
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 800, heightDp = 700)
@Composable
private fun QueueTabletPreview() = QueuePreview()
