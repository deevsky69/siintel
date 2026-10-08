package id.polri.jaksel.laporpresisi

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Call
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.TextButton
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.polri.jaksel.laporpresisi.ui.BrandHeader
import id.polri.jaksel.laporpresisi.ui.CriticalPanel
import id.polri.jaksel.laporpresisi.ui.Hint
import id.polri.jaksel.laporpresisi.ui.InputField
import id.polri.jaksel.laporpresisi.ui.PresisiColors
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import id.polri.jaksel.laporpresisi.ui.PrimaryButton
import id.polri.jaksel.laporpresisi.ui.ScreenScaffold
import id.polri.jaksel.laporpresisi.ui.SecondaryButton
import id.polri.jaksel.laporpresisi.ui.SectionLabel

/**
 * Isi layar muka. Murni tampilan: seluruh data datang lewat [state], seluruh aksi keluar
 * lewat callback — supaya dapat dipratinjau di Android Studio tanpa jaringan dan tanpa
 * Activity. Alasan susunannya (imbauan SEBELUM tombol lapor, 110 di atas segalanya, tombol
 * status hanya bila pernah melapor) ada pada dokumentasi [MainActivity].
 */
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
        AlertDialog(
            onDismissRequest = onPanicCancel,
            containerColor = PresisiColors.Base900,
            titleContentColor = PresisiColors.Ink,
            textContentColor = PresisiColors.InkMuted,
            title = { Text(stringResource(R.string.panic_confirm_title)) },
            text = {
                Column {
                    Text(stringResource(R.string.panic_confirm_body))
                    InputField(
                        label = stringResource(R.string.panic_note_hint),
                        value = state.panicNote,
                        onValueChange = onPanicNote,
                        maxLength = 300,
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = onPanicConfirm,
                    colors = ButtonDefaults.buttonColors(containerColor = PresisiColors.Critical, contentColor = PresisiColors.Ink),
                ) { Text(stringResource(R.string.panic_confirm_yes), fontWeight = FontWeight.Bold) }
            },
            dismissButton = {
                TextButton(onClick = onPanicCancel) { Text(stringResource(R.string.panic_confirm_no), color = PresisiColors.InkMuted) }
            },
        )
    }
    ScreenScaffold(horizontalPadding = 24.dp, verticalPadding = 32.dp) {
    BrandHeader(stringResource(R.string.app_name), stringResource(R.string.subtitle))

    Text(
        stringResource(R.string.home_lead),
        style = MaterialTheme.typography.bodyMedium,
        modifier = Modifier.padding(top = 20.dp),
    )

    CriticalPanel(Modifier.padding(top = 20.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Call, contentDescription = null, tint = PresisiColors.Critical, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(10.dp))
            Text(
                stringResource(R.string.emergency_title),
                color = PresisiColors.Critical,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
            )
        }
    }

    PanicSection(state, onPanicPress)

    if (state.alerts.isNotEmpty()) {
        Spacer(Modifier.height(20.dp))
        SectionLabel(stringResource(R.string.home_alerts_title), icon = Icons.Outlined.Notifications)
        for (row in state.alerts) {
            AlertCard(row, Modifier.padding(top = 8.dp))
        }
        Hint(stringResource(R.string.home_alerts_basis), Modifier.padding(top = 8.dp))
    }

    Spacer(Modifier.height(26.dp))
    PrimaryButton(stringResource(R.string.home_report), onClick = onReport, icon = Icons.Outlined.Edit)
    Hint(stringResource(R.string.home_report_hint), Modifier.padding(top = 8.dp))

    if (state.hasTicket) {
        Spacer(Modifier.height(12.dp))
        SecondaryButton(stringResource(R.string.home_status), onClick = onCheckStatus, icon = Icons.Outlined.Search)
        state.statusResult?.let {
            Text(
                it,
                style = MaterialTheme.typography.bodyMedium,
                fontSize = 13.sp,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }

    Spacer(Modifier.height(24.dp))
    SecondaryButton(stringResource(R.string.home_officer), onClick = onOfficer, icon = Icons.Outlined.Lock)
    Hint(stringResource(R.string.home_officer_hint), Modifier.padding(top = 8.dp))

    Text(
        "${stringResource(R.string.version_label)} ${state.version}",
        style = MaterialTheme.typography.bodySmall,
        modifier = Modifier
            .padding(top = 32.dp)
            .align(Alignment.CenterHorizontally),
    )
    }
}

/**
 * Tombol darurat (8 Oktober 2026): besar, merah, dua langkah (tekan → konfirmasi) supaya
 * tidak tertekan di saku. Setelah terkirim menampilkan kode dan kelurahan yang dikirim.
 * 110 selalu disebut: kanal ini memberi tahu petugas, bukan menggantikan jalur resmi.
 */
@Composable
private fun PanicSection(state: HomeState, onPress: () -> Unit) {
    Column(Modifier.padding(top = 16.dp)) {
        when (val panic = state.panic) {
            is PanicState.Sent -> CriticalPanel {
                Text(
                    stringResource(R.string.panic_sent, panic.code),
                    color = PresisiColors.Ok,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                )
                Text(
                    panic.area?.let { stringResource(R.string.panic_sent_area, it) }
                        ?: stringResource(R.string.panic_sent_no_area),
                    style = MaterialTheme.typography.bodyMedium,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(top = 4.dp),
                )
                Text(stringResource(R.string.panic_hint), style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 6.dp))
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
                shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = PresisiColors.Critical,
                    contentColor = PresisiColors.Ink,
                    disabledContainerColor = PresisiColors.Critical.copy(alpha = 0.6f),
                    disabledContentColor = PresisiColors.Ink,
                ),
                modifier = Modifier.fillMaxWidth().height(64.dp),
            ) {
                if (sending) {
                    CircularProgressIndicator(color = PresisiColors.Ink, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                    Spacer(Modifier.width(12.dp))
                    Text(stringResource(R.string.panic_sending), fontWeight = FontWeight.Bold)
                } else {
                    Icon(Icons.Outlined.Warning, contentDescription = null, modifier = Modifier.size(24.dp))
                    Spacer(Modifier.width(12.dp))
                    Text(stringResource(R.string.panic_button), fontWeight = FontWeight.Bold, fontSize = 17.sp, letterSpacing = 1.sp)
                }
            }
            Hint(stringResource(R.string.panic_hint), Modifier.padding(top = 6.dp))
        }
    }
}

/**
 * Satu imbauan. Sengaja tanpa aksi klik: imbauan adalah kanal SATU ARAH, dan rincian yang
 * ada di sistem justru yang tidak boleh keluar.
 */
@Composable
private fun AlertCard(row: PublicApi.Imbauan, modifier: Modifier = Modifier) {
    val jam = row.timeWindow?.let { " · $it WIB" } ?: ""
    CriticalPanel(modifier) {
        Text(
            "${row.threatType} · ${row.areaText}$jam",
            color = PresisiColors.Critical,
            fontWeight = FontWeight.Bold,
            fontSize = 13.sp,
        )
        Text(
            row.message,
            style = MaterialTheme.typography.bodyMedium,
            fontSize = 13.sp,
            modifier = Modifier.padding(top = 4.dp),
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 780)
@Composable
private fun HomePreview() {
    PresisiTheme {
        HomeScreen(
            state = HomeState(
                alerts = listOf(
                    PublicApi.Imbauan(
                        code = "PAL-0026",
                        threatType = "CURANMOR",
                        areaText = "Kecamatan Tebet",
                        timeWindow = "18:00-23:59",
                        message = "Imbauan kewaspadaan. Kunci ganda kendaraan Anda dan parkir di tempat terang.",
                    ),
                ),
                hasTicket = true,
                statusResult = "CR-2026-0001 · Diverifikasi\nDiputuskan petugas triase.",
                version = "2.2.0",
            ),
            onReport = {},
            onOfficer = {},
            onCheckStatus = {},
        )
    }
}
