#!/bin/bash

# Git prompt function (adapted from your .bashrc)
git_prompt() {
    # Check if we're in a git repo
    if git --no-optional-locks rev-parse --git-dir > /dev/null 2>&1; then
        # Get branch name
        local branch=$(git --no-optional-locks branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/')

        # Get git status indicators
        local git_status=""

        # Check for uncommitted changes
        if [[ $(git --no-optional-locks status --porcelain 2> /dev/null) ]]; then
            git_status="${git_status}*"
        fi

        # Check for staged changes
        if git --no-optional-locks diff --cached --quiet 2> /dev/null; then
            :
        else
            git_status="${git_status}+"
        fi

        # Check if ahead/behind remote (skip locks for performance)
        local upstream=$(git --no-optional-locks rev-parse --abbrev-ref --symbolic-full-name @{u} 2> /dev/null)
        if [[ -n "$upstream" ]]; then
            local ahead=$(git --no-optional-locks rev-list @{u}..HEAD --count 2> /dev/null)
            local behind=$(git --no-optional-locks rev-list HEAD..@{u} --count 2> /dev/null)

            if [[ $ahead -gt 0 ]]; then
                git_status="${git_status}↑${ahead}"
            fi

            if [[ $behind -gt 0 ]]; then
                git_status="${git_status}↓${behind}"
            fi
        fi

        # Format the output with colors
        printf " \033[35m($branch$git_status)\033[0m"
    fi
}

# Main status line output
printf "\033[32m$(whoami)@$(hostname -s)\033[0m:\033[34m$(pwd)\033[0m$(git_prompt)"