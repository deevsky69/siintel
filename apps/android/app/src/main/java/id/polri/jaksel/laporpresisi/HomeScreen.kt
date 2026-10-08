package id.polri.jaksel.laporpresisi

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.polri.jaksel.laporpresisi.ui.BrandMark
import id.polri.jaksel.laporpresisi.ui.CriticalPanel
import id.polri.jaksel.laporpresisi.ui.InputField
import id.polri.jaksel.laporpresisi.ui.Panel
import id.polri.jaksel.laporpresisi.ui.PresisiColors
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import id.polri.jaksel.laporpresisi.ui.PrimaryButton
import id.polri.jaksel.laporpresisi.ui.ScreenScaffold

/** Keadaan tombol darurat: diam → konfirmasi → mengirim → tanda terima / gagal. */
sealed interface PanicState {
    data object Idle : PanicState
    data object Confirming : PanicState
    data object Sending : PanicState
    data class Sent(val code: String, val area: String?) : PanicState
    data class Failed(val reason: String) : PanicState
}

data class HomeState(
    val alerts: List<PublicApi.Imbauan> = emptyList(),
    val hasTicket: Boolean = false,
    /** Hasil cek status; `null` berarti belum ditekan. */
    val statusResult: String? = null,
    val version: String = "",
    val panic: PanicState = PanicState.Idle,
    val panicNote: String = "",
)

/**
 * Layar muka warga, disusun ulang 8 Oktober 2026 setelah pemilik proyek menilai versi
 * sebelumnya terlalu padat (tiga tombol bertumpuk, imbauan, kotak darurat, hint di mana-mana).
 *
 * Polanya mengikuti aplikasi darurat warga yang diteliti (112 India, SOS Grab, JakLapor):
 * **satu tindakan darurat yang besar, satu tindakan utama, selebihnya kecil**. Yang
 * dibutuhkan orang yang panik hanya tombol merah; yang ingin melapor hanya satu tombol;
 * petugas tahu harus mencari tautan masuk di bawah. Imbauan dilipat menjadi satu baris
 * dengan jumlah — dibuka bila diminta.
 */
@Composable
fun HomeScreen(
    state: HomeState,
    onReport: () -> Unit,
    onOfficer: () -> Unit,
    onCheckStatus: () -> Unit,
    onPanicPress: () -> Unit = {},
    onPanicConfirm: () -> Unit = {},
    onPanicCancel: () -> Unit = {},
    onPanicNote: (String) -> Unit = {},
) {
    if (state.panic is PanicState.Confirming) {
        PanicConfirmDialog(state.panicNote, onPanicNote, onPanicConfirm, onPanicCancel)
    }
    ScreenScaffold(horizontalPadding = 24.dp, verticalPadding = 28.dp) {
        // Kepala: lambang kecil dan nama — bukan poster.
        Row(verticalAlignment = Alignment.CenterVertically) {
            BrandMark(44.dp)
            Spacer(Modifier.width(12.dp))
            Column {
                Text(stringResource(R.string.app_name), style = MaterialTheme.typography.titleMedium, fontSize = 20.sp, letterSpacing = 3.sp)
                Text(stringResource(R.string.subtitle), style = MaterialTheme.typography.bodySmall)
            }
        }

        Text(
            stringResource(R.string.home_lead),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 18.dp),
        )

        // 1. Lapor — tindakan utama aplikasi ini.
        PrimaryButton(
            stringResource(R.string.home_report),
            onClick = onReport,
            icon = Icons.Outlined.Edit,
            modifier = Modifier.padding(top = 20.dp),
        )
        if (state.hasTicket) {
            StatusRow(state.statusResult, onCheckStatus)
        }

        // 2. Darurat — tepat di bawahnya, berukuran sama, mencolok karena warnanya
        //    (pilihan B pemilik proyek, 8 Oktober 2026; pola SOS Grab, bukan 112 India).
        PanicSection(state, onPanicPress)

        // 3. Imbauan — satu baris, dibuka bila diminta.
        if (state.alerts.isNotEmpty()) {
            AlertsCompact(state.alerts)
        }

        // 4. Petugas — tautan kecil, bukan tombol ketiga.
        Spacer(Modifier.height(28.dp))
        Row(
            Modifier
                .fillMaxWidth()
                .clickable(onClick = onOfficer)
                .padding(vertical = 8.dp),
            horizontalArrangement = androidx.compose.foundation.layout.Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.Lock, contentDescription = null, tint = PresisiColors.InkMuted, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(6.dp))
            Text(stringResource(R.string.home_officer_link), color = PresisiColors.InkMuted, fontSize = 13.sp)
        }
        Text(
            "${stringResource(R.string.version_label)} ${state.version}",
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
        )
    }
}

@Composable
private fun PanicConfirmDialog(note: String, onNote: (String) -> Unit, onConfirm: () -> Unit, onCancel: () -> Unit) {
    AlertDialog(
        onDismissRequest = onCancel,
        containerColor = PresisiColors.Base900,
        titleContentColor = PresisiColors.Ink,
        textContentColor = PresisiColors.InkMuted,
        title = { Text(stringResource(R.string.panic_confirm_title)) },
        text = {
            Column {
                Text(stringResource(R.string.panic_confirm_body))
                InputField(stringResource(R.string.panic_note_hint), note, onNote, maxLength = 300)
            }
        },
        confirmButton = {
            Button(
                onClick = onConfirm,
                colors = ButtonDefaults.buttonColors(containerColor = PresisiColors.Critical, contentColor = PresisiColors.Ink),
            ) { Text(stringResource(R.string.panic_confirm_yes), fontWeight = FontWeight.Bold) }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text(stringResource(R.string.panic_confirm_no), color = PresisiColors.InkMuted) }
        },
    )
}

/**
 * Tombol darurat: besar, merah, dua langkah (tekan → konfirmasi) supaya tidak tertekan di
 * saku. Setelah terkirim: kode dan kelurahan yang dikirim. Di bawahnya hanya satu kalimat:
 * 110 tetap jalur resmi.
 */
@Composable
private fun PanicSection(state: HomeState, onPress: () -> Unit) {
    Column(Modifier.padding(top = 10.dp)) {
        when (val panic = state.panic) {
            is PanicState.Sent -> CriticalPanel {
                Text(stringResource(R.string.panic_sent, panic.code), color = PresisiColors.Ok, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                Text(
                    panic.area?.let { stringResource(R.string.panic_sent_area, it) } ?: stringResource(R.string.panic_sent_no_area),
                    style = MaterialTheme.typography.bodyMedium,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(top = 4.dp),
                )
                Text(stringResource(R.string.emergency_title), color = PresisiColors.Critical, fontWeight = FontWeight.SemiBold, fontSize = 13.sp, modifier = Modifier.padding(top = 8.dp))
            }
            is PanicState.Failed -> CriticalPanel(Modifier.padding(bottom = 8.dp)) {
                Text(stringResource(R.string.panic_failed, panic.reason), color = PresisiColors.Critical, fontSize = 13.sp)
            }
            else -> Unit
        }
        if (state.panic !is PanicState.Sent) {
            val sending = state.panic is PanicState.Sending
            Button(
                onClick = onPress,
                enabled = !sending,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PresisiColors.Critical,
                    contentColor = PresisiColors.Ink,
                    disabledContainerColor = PresisiColors.Critical.copy(alpha = 0.6f),
                    disabledContentColor = PresisiColors.Ink,
                ),
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                if (sending) {
                    CircularProgressIndicator(color = PresisiColors.Ink, strokeWidth = 2.dp, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(10.dp))
                    Text(stringResource(R.string.panic_sending), fontWeight = FontWeight.Bold)
                } else {
                    Icon(Icons.Outlined.Warning, contentDescription = null, modifier = Modifier.size(20.dp))
                    Spacer(Modifier.width(10.dp))
                    Text(stringResource(R.string.panic_button_short), fontWeight = FontWeight.Bold, fontSize = 15.sp)
                }
            }
            Text(
                stringResource(R.string.panic_hint_short),
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
            )
        }
    }
}

/** Cek status laporan terakhir: satu baris teks yang dapat diketuk, bukan tombol ketiga. */
@Composable
private fun StatusRow(result: String?, onCheck: () -> Unit) {
    Column(Modifier.padding(top = 6.dp)) {
        Row(
            Modifier.clickable(onClick = onCheck).padding(vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.Search, contentDescription = null, tint = PresisiColors.Accent, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(6.dp))
            Text(stringResource(R.string.home_status), color = PresisiColors.Accent, fontSize = 13.sp)
        }
        if (result != null) {
            Text(result, style = MaterialTheme.typography.bodyMedium, fontSize = 13.sp)
        }
    }
}

/**
 * Imbauan yang berlaku, dilipat: satu baris berjumlah, dibuka bila diminta. Tetap SATU ARAH
 * (tanpa tautan ke rincian) — rincian yang ada di sistem justru yang tidak boleh keluar.
 */
@Composable
private fun AlertsCompact(alerts: List<PublicApi.Imbauan>) {
    var open by remember { mutableStateOf(false) }
    Panel(Modifier.padding(top = 18.dp)) {
        Row(Modifier.clickable { open = !open }, verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Notifications, contentDescription = null, tint = PresisiColors.Warning, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(10.dp))
            Text(
                stringResource(R.string.home_alerts_compact, alerts.size),
                style = MaterialTheme.typography.bodyLarge,
                fontSize = 14.sp,
                modifier = Modifier.weight(1f),
            )
            Text(
                stringResource(if (open) R.string.home_alerts_hide else R.string.home_alerts_show),
                color = PresisiColors.Accent,
                fontSize = 13.sp,
            )
        }
        if (open) {
            for (row in alerts) {
                val jam = row.timeWindow?.let { " · $it WIB" } ?: ""
                Column(Modifier.padding(top = 10.dp)) {
                    Text("${row.threatType} · ${row.areaText}$jam", color = PresisiColors.Warning, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                    Text(row.message, style = MaterialTheme.typography.bodyMedium, fontSize = 13.sp, modifier = Modifier.padding(top = 2.dp))
                }
            }
            Text(stringResource(R.string.home_alerts_basis), style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 10.dp))
        }
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 760)
@Composable
private fun HomePreview() {
    PresisiTheme {
        HomeScreen(
            state = HomeState(
                alerts = listOf(
                    PublicApi.Imbauan("PAL-0026", "CURANMOR", "Kecamatan Tebet", "18:00-23:59", "Kunci ganda kendaraan Anda dan parkir di tempat terang."),
                ),
                hasTicket = true,
                version = "2.7.0",
            ),
            onReport = {},
            onOfficer = {},
            onCheckStatus = {},
        )
    }
}
