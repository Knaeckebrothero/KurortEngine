{{- define "kurort.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kurort.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "kurort.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "kurort.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "kurort.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kurort.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: web
{{- end -}}

{{- define "kurort.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "kurort.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kurort.postgresql.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kurort.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: database
{{- end -}}

{{/* Secret + key that hold the application's database URL. */}}
{{- define "kurort.databaseSecretName" -}}
{{- if .Values.postgresql.enabled -}}
{{- include "kurort.postgresql.fullname" . -}}
{{- else if .Values.externalDatabase.existingSecret -}}
{{- .Values.externalDatabase.existingSecret -}}
{{- else if .Values.externalDatabase.url -}}
{{- printf "%s-database" (include "kurort.fullname" .) -}}
{{- else -}}
{{- fail "set postgresql.enabled=true, externalDatabase.existingSecret or externalDatabase.url" -}}
{{- end -}}
{{- end -}}

{{- define "kurort.databaseSecretKey" -}}
{{- if or .Values.postgresql.enabled (not .Values.externalDatabase.existingSecret) -}}
database-url
{{- else -}}
{{- .Values.externalDatabase.existingSecretKey -}}
{{- end -}}
{{- end -}}

{{- define "kurort.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}

{{/* Environment shared by the app container and its init containers. */}}
{{- define "kurort.env" -}}
- name: KURORT_DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "kurort.databaseSecretName" . }}
      key: {{ include "kurort.databaseSecretKey" . }}
- name: KURORT_HOTEL_NAME
  value: {{ .Values.app.hotelName | quote }}
- name: KURORT_HOTEL_CITY
  value: {{ .Values.app.hotelCity | quote }}
{{- with .Values.app.today }}
- name: KURORT_TODAY
  value: {{ . | quote }}
{{- end }}
- name: HOME
  value: /tmp
{{- range $name, $value := .Values.app.extraEnv }}
- name: {{ $name }}
  value: {{ $value | quote }}
{{- end }}
{{- end -}}
