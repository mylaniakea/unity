{{/*
Expand the name of the chart.
*/}}
{{- define "unity.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "unity.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "unity.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "unity.labels" -}}
helm.sh/chart: {{ include "unity.chart" . }}
{{ include "unity.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "unity.selectorLabels" -}}
app.kubernetes.io/name: {{ include "unity.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "unity.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "unity.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "unity.postgresql.host" -}}
{{- if .Values.postgresql.external.enabled }}
{{- .Values.postgresql.external.host }}
{{- else }}
{{- printf "%s-postgresql" (include "unity.fullname" .) }}
{{- end }}
{{- end }}

{{/*
PostgreSQL connection string
*/}}
{{- define "unity.postgresql.connectionString" -}}
{{- $host := include "unity.postgresql.host" . }}
{{- $port := .Values.postgresql.external.port | default 5432 }}
{{- $user := .Values.postgresql.auth.username }}
{{- $db := .Values.postgresql.auth.database }}
{{- printf "postgresql+psycopg2://%s:${POSTGRES_PASSWORD}@%s:%d/%s" $user $host (int $port) $db }}
{{- end }}
