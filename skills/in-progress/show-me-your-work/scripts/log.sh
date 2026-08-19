#!/bin/sh
# Append a well-formed row to a show-me-your-work decision log (TSV).
# Usage: log.sh <logfile> <phase> <decision> <why> <evidence> <result>
set -eu

if [ "$#" -ne 6 ]; then
	printf 'usage: log.sh <logfile> <phase> <decision> <why> <evidence> <result>\n' >&2
	exit 1
fi

logfile="$1"
shift

for field in "$@"; do
	if [ -z "$field" ]; then
		printf 'log.sh: every field must be non-empty (phase, decision, why, evidence, result)\n' >&2
		exit 1
	fi
done

logdir="$(dirname "$logfile")"
if [ -n "$logdir" ] && [ "$logdir" != "." ] && [ ! -d "$logdir" ]; then
	mkdir -p "$logdir"
fi

header='ts	phase	decision	why	evidence	result'
if [ ! -f "$logfile" ]; then
	printf '%s\n' "$header" > "$logfile"
else
	firstline=$(head -n 1 "$logfile")
	if [ "$firstline" != "$header" ]; then
		printf 'log.sh: %s exists but its header is not the decision-log header; refusing to append\n' "$logfile" >&2
		exit 1
	fi
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Strip tabs/newlines/CR so cells stay on one line, and prefix any cell
# whose first char a spreadsheet would parse as a formula (=, +, -, @)
# with a single quote. The skill expects this log to be read in
# spreadsheets, so attacker-controlled evidence (PR titles, filenames,
# generated text) must not become formula execution when a reviewer
# opens the file.
clean() {
	v=$(printf '%s' "$1" | tr '\t\n\r' '   ')
	case "$v" in
		=*|+*|-*|@*) printf "'%s" "$v" ;;
		*) printf '%s' "$v" ;;
	esac
}
# Clean every cell before touching the file, so a failed tr can never
# append a partial or empty row.
c1=$(clean "$1")
c2=$(clean "$2")
c3=$(clean "$3")
c4=$(clean "$4")
c5=$(clean "$5")
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$ts" "$c1" "$c2" "$c3" "$c4" "$c5" >> "$logfile"
