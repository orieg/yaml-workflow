{{/*
Common labels
*/}}
{{- define "yaml-workflow.labels" -}}
app.kubernetes.io/name: yaml-workflow
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "yaml-workflow.selectorLabels" -}}
app.kubernetes.io/name: yaml-workflow
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Image tag — defaults to Chart.AppVersion
*/}}
{{- define "yaml-workflow.imageTag" -}}
{{- .Values.image.tag | default .Chart.AppVersion -}}
{{- end }}
