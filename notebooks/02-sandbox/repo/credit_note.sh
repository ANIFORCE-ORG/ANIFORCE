#!/bin/sh

customer="$1"
amount="${2#-}"

printf 'Credit note for %s: $%s credit.\n' "$customer" "$amount"
