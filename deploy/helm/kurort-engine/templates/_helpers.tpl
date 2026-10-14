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
{{ include "kurort.auth.env" . }}
{{- range $name, $value := .Values.app.extraEnv }}
- name: {{ $name }}
  value: {{ $value | quote }}
{{- end }}
{{- end -}}

{{/* ---- Authentication (OIDC) ---- */}}

{{- define "kurort.auth.secretName" -}}
{{- printf "%s-auth" (include "kurort.fullname" .) -}}
{{- end -}}

{{- define "kurort.auth.publicUrl" -}}
{{- if .Values.auth.publicUrl -}}
{{- trimSuffix "/" .Values.auth.publicUrl -}}
{{- else if .Values.ingress.enabled -}}
{{- printf "%s://%s" (ternary "https" "http" (not (empty .Values.ingress.tls))) .Values.ingress.host -}}
{{- end -}}
{{- end -}}

{{/* Fail the render early instead of shipping a pod that cannot log anyone in. */}}
{{- define "kurort.auth.validate" -}}
{{- if .Values.auth.enabled -}}
{{- if not .Values.auth.oidc.issuer -}}
{{- fail "auth.enabled=true needs auth.oidc.issuer (the OIDC issuer URL), or set auth.enabled=false for a login-free local run" -}}
{{- end -}}
{{- if not (or .Values.auth.oidc.clientSecret .Values.auth.oidc.existingSecret) -}}
{{- fail "auth.enabled=true needs auth.oidc.clientSecret or auth.oidc.existingSecret for the confidential OIDC client" -}}
{{- end -}}
{{- if not (include "kurort.auth.publicUrl" .) -}}
{{- fail "auth.enabled=true needs auth.publicUrl when the ingress is disabled (it builds the OIDC redirect URI)" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "kurort.auth.env" -}}
- name: KURORT_AUTH
  value: {{ ternary "oidc" "off" .Values.auth.enabled | quote }}
{{- if .Values.auth.enabled }}
- name: KURORT_PUBLIC_URL
  value: {{ include "kurort.auth.publicUrl" . | quote }}
- name: KURORT_OIDC_ISSUER
  value: {{ .Values.auth.oidc.issuer | quote }}
- name: KURORT_OIDC_INTERNAL_URL
  value: {{ .Values.auth.oidc.internalUrl | default .Values.auth.oidc.issuer | quote }}
- name: KURORT_OIDC_CLIENT_ID
  value: {{ .Values.auth.oidc.clientId | quote }}
- name: KURORT_OIDC_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      {{- if .Values.auth.oidc.existingSecret }}
      name: {{ .Values.auth.oidc.existingSecret }}
      key: {{ .Values.auth.oidc.existingSecretKey }}
      {{- else }}
      name: {{ include "kurort.auth.secretName" . }}
      key: client-secret
      {{- end }}
- name: KURORT_SESSION_SECRET
  valueFrom:
    secretKeyRef:
      {{- if .Values.auth.session.existingSecret }}
      name: {{ .Values.auth.session.existingSecret }}
      key: {{ .Values.auth.session.existingSecretKey }}
      {{- else }}
      name: {{ include "kurort.auth.secretName" . }}
      key: session-secret
      {{- end }}
{{- end }}
{{- end -}}
