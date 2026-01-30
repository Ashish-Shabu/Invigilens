package com.invigilens.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                val vm: AlertViewModel = viewModel(factory = AlertViewModelFactory())
                val state by vm.state.collectAsState()
                AlertListScreen(
                    state = state,
                    onRefresh = { vm.refreshAlerts() },
                    onVerify = { vm.updateStatus(it, "verified") },
                    onReject = { vm.updateStatus(it, "rejected") },
                    onSelect = { vm.selectAlert(it) },
                    onCloseDetail = { vm.selectAlert(null) }
                )
            }
        }
    }
}

@Composable
fun AlertListScreen(
    state: AlertUiState,
    onRefresh: () -> Unit,
    onVerify: (String) -> Unit,
    onReject: (String) -> Unit,
    onSelect: (String) -> Unit,
    onCloseDetail: () -> Unit,
) {
    val primaryColor = MaterialTheme.colorScheme.primary
    
    Surface(modifier = Modifier.fillMaxSize(), color = Color.White) {
        LazyColumn(
            modifier = Modifier.padding(24.dp).fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. Header Section
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.Bottom,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(
                            "SYSTEM_STATUS // V1.0",
                            style = MaterialTheme.typography.labelSmall,
                            color = primaryColor.copy(alpha = 0.6f),
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 2.sp
                        )
                        Text(
                            "Alerts Feed",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Black,
                            color = Color.Black
                        )
                    }
                    
                    Box(
                        modifier = Modifier
                            .border(1.dp, primaryColor, RoundedCornerShape(4.dp))
                            .clickable(enabled = !state.loading) { onRefresh() }
                            .padding(horizontal = 14.dp, vertical = 8.dp)
                    ) {
                        Text(
                            if (state.loading) "SYNCING..." else "REFRESH",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.ExtraBold,
                            color = primaryColor,
                            letterSpacing = 1.sp
                        )
                    }
                }
            }
            
            // 2. Status Chips
            item {
                Spacer(modifier = Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    TechnicalBadge(label = "NETWORK", active = state.online)
                    TechnicalBadge(label = "STREAM", active = state.socketConnected)
                }
                Spacer(modifier = Modifier.height(16.dp))
            }

            // 3. Error Message
            if (state.error != null) {
                item {
                    Text(
                        "LOG_ERROR: ${state.error}",
                        color = Color.Red,
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier
                            .background(Color.Red.copy(alpha = 0.05f))
                            .border(1.dp, Color.Red.copy(alpha = 0.2f))
                            .padding(8.dp)
                            .fillMaxWidth()
                    )
                }
            }

            // 4. Alert List
            items(state.alerts) { alert ->
                TechnicalAlertItem(
                    alert = alert,
                    onSelect = { onSelect(alert.id) },
                    onVerify = { onVerify(alert.id) },
                    onReject = { onReject(alert.id) }
                )
            }
        }

        // Popup Dialog for Evidence
        if (state.selectedAlert != null) {
            androidx.compose.ui.window.Dialog(onDismissRequest = onCloseDetail) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color.White, RoundedCornerShape(4.dp))
                        .padding(0.dp) 
                ) {
                    AlertDataPanel(
                        alert = state.selectedAlert,
                        loading = state.detailLoading,
                        onVerify = { state.selectedAlert?.id?.let(onVerify) },
                        onReject = { state.selectedAlert?.id?.let(onReject) },
                        onClose = onCloseDetail
                    )
                }
            }
        }
    }
}

@Composable
fun TechnicalBadge(label: String, active: Boolean) {
    val primary = MaterialTheme.colorScheme.primary
    val color = if (active) primary else Color.Black.copy(alpha = 0.2f)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .border(1.dp, color.copy(alpha = 0.4f), RoundedCornerShape(2.dp))
            .padding(horizontal = 10.dp, vertical = 4.dp)
    ) {
        Box(
            modifier = Modifier
                .size(6.dp)
                .background(if (active) color else Color.Transparent, CircleShape)
                .then(if (!active) Modifier.border(1.dp, color, CircleShape) else Modifier)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Black,
            color = color,
            letterSpacing = 1.sp
        )
    }
}

@Composable
fun TechnicalAlertItem(
    alert: AlertDto,
    onSelect: () -> Unit,
    onVerify: () -> Unit,
    onReject: () -> Unit
) {
    val primary = MaterialTheme.colorScheme.primary
    val formatter = remember {
        DateTimeFormatter.ofPattern("HH:mm:ss").withZone(ZoneId.systemDefault())
    }
    
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onSelect() }
            .background(Color.White)
            .border(1.dp, Color.Black.copy(alpha = 0.08f), RoundedCornerShape(2.dp))
    ) {
        // Monocolour Accent Bar
        Box(modifier = Modifier.fillMaxWidth().height(4.dp).background(primary.copy(alpha = 0.15f)))
        
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.Top) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        alert.violationType.uppercase(),
                        style = MaterialTheme.typography.labelSmall,
                        color = primary,
                        fontWeight = FontWeight.Black,
                        letterSpacing = 1.5.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "STUDENT_${alert.studentId}",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = Color.Black
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        "${(alert.confidence * 100).toInt()}%",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Black,
                        color = primary
                    )
                    val timeString = runCatching { formatter.format(Instant.parse(alert.timestamp)) }.getOrDefault("--:--:--")
                    Text(
                        timeString,
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.Gray,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(20.dp))
            
            // Minimalist Action Row
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .background(primary)
                        .clickable { onVerify() }
                        .padding(vertical = 12.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text("VERIFY", color = Color.White, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Black, letterSpacing = 1.sp)
                }
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .border(1.dp, primary, RoundedCornerShape(2.dp))
                        .clickable { onReject() }
                        .padding(vertical = 12.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text("REJECT", color = primary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Black, letterSpacing = 1.sp)
                }
            }
        }
    }
}

@Composable
fun AlertDataPanel(
    alert: AlertDto?,
    loading: Boolean,
    onVerify: () -> Unit,
    onReject: () -> Unit,
    onClose: () -> Unit
) {
    if (alert == null) return
    val primary = MaterialTheme.colorScheme.primary

    Spacer(modifier = Modifier.height(24.dp))
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(primary.copy(alpha = 0.02f))
            .border(1.dp, primary, RoundedCornerShape(4.dp))
            .padding(20.dp)
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text("EVIDENCE_LOG // ${alert.id}", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Black, color = primary, letterSpacing = 1.sp)
            Text(
                "[ CLOSE ]",
                modifier = Modifier.clickable { onClose() },
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
                color = Color.Gray
            )
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        if (loading) {
            Box(modifier = Modifier.fillMaxWidth().height(120.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = primary, strokeWidth = 2.dp)
            }
        } else {
            Text(alert.violationType, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            Spacer(modifier = Modifier.height(12.dp))
            TechnicalEvidencePreview(evidencePath = alert.evidencePath)
            Spacer(modifier = Modifier.height(20.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(
                    onClick = onVerify,
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(2.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = primary)
                ) {
                    Text("APPROVE", fontWeight = FontWeight.Black, letterSpacing = 1.sp)
                }
                Button(
                    onClick = onReject,
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(2.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent, contentColor = primary),
                    border = BorderStroke(1.dp, primary)
                ) {
                    Text("REJECT", fontWeight = FontWeight.Black, letterSpacing = 1.sp)
                }
            }
        }
    }
}

@Composable
fun TechnicalEvidencePreview(evidencePath: String?) {
    val primary = MaterialTheme.colorScheme.primary
    if (evidencePath.isNullOrBlank()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp)
                .background(Color.Black.copy(alpha = 0.03f))
                .border(1.dp, Color.Black.copy(alpha = 0.05f)),
            contentAlignment = Alignment.Center
        ) {
            Text("NO_VISUAL_LOG", style = MaterialTheme.typography.labelSmall, color = Color.Gray.copy(alpha = 0.5f), fontWeight = FontWeight.Bold)
        }
        return
    }
    
    val fullUrl = if (evidencePath.startsWith("http")) evidencePath else "http://10.0.2.2:5000/evidence/$evidencePath"
    val isVideo = evidencePath.endsWith(".mp4", true) || evidencePath.endsWith(".webm", true)

    Box(modifier = Modifier.fillMaxWidth().border(1.dp, Color.Black.copy(alpha = 0.1f))) {
        if (isVideo) {
            TechnicalVideoPlayer(url = fullUrl)
        } else {
            AsyncImage(
                model = fullUrl,
                contentDescription = "Evidence image",
                modifier = Modifier.fillMaxWidth().height(220.dp)
            )
        }
    }
}

@Composable
fun TechnicalVideoPlayer(url: String) {
    val context = LocalContext.current
    val exoPlayer = remember(url) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(url))
            prepare()
            playWhenReady = true
        }
    }

    Box(modifier = Modifier.fillMaxWidth().height(220.dp)) {
        AndroidView(factory = {
            PlayerView(it).apply {
                player = exoPlayer
                useController = true
                setShowNextButton(false)
                setShowPreviousButton(false)
            }
        }, modifier = Modifier.fillMaxSize())
    }

    DisposableEffect(exoPlayer) {
        onDispose {
            exoPlayer.release()
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun AlertListScreenPreview() {
    MaterialTheme {
        AlertListScreen(
            state = AlertUiState(
                alerts = listOf(
                    AlertDto(id = "1", studentId = "STU001", violationType = "Using Phone", confidence = 0.95, timestamp = "2024-01-20T14:30:00Z", status = "pending"),
                    AlertDto(id = "2", studentId = "STU002", violationType = "Giving object", confidence = 0.87, timestamp = "2024-01-20T14:25:00Z", status = "verified"),
                ),
                online = true,
                socketConnected = true
            ),
            onRefresh = {},
            onVerify = {},
            onReject = {},
            onSelect = {},
            onCloseDetail = {}
        )
    }
}
