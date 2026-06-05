---
title: "Read to Remember"
description: "A personal reading log and research tool built as a replacement for Goodreads — organised around a 'personal encyclopedia' model of reading rather than a review model."
url: "https://zidwago.github.io/read-to-remember"
repo: "https://github.com/zidwago/read-to-remember"
stack: [JavaScript, D3.js, Supabase, Anthropic API, GitHub Pages]
status: live
created: 2024-01-01
modified: 2026-06-04
---

## What it is

Read to Remember is a personal reading log web app I built to replace Goodreads. Goodreads is badly outdated — its interface hasn't meaningfully changed in years, and its model (rating books, writing reviews) doesn't fit how I actually read.

The app is built around a different model: the *personal encyclopedia*. The idea comes from Adam Walker, an English literature scholar, who described his reading log not as a record of books consumed but as a growing reference work — a tool for thinking, not just tracking.

## What it does

- **Timeline view** — a D3.js visualization of reading over time, organized chronologically
- **Engagement levels** — instead of ratings, each entry carries an engagement level: close reading, read, consulted, skimmed, referenced. This captures how you engaged with a text, not just whether you liked it.
- **Weekly check-in** — a structured weekly prompt (in progress) for reflecting on what you've read and what it's connected to
- **Anthropic API integration** — AI-assisted features for surfacing connections between texts and generating reading reflections

## Why I built it

I read a lot of philosophy. Goodreads doesn't accommodate the way philosophy gets read — you return to texts, consult them, work through sections over months, change your assessment as you understand more. A log built around a star rating and a review misses all of this.

The app is primarily a personal tool. Whether it becomes something more is an open question.

## Stack

Built with vanilla JavaScript, D3.js for visualization, Supabase for the backend, and the Anthropic API for AI features. Deployed on GitHub Pages.
