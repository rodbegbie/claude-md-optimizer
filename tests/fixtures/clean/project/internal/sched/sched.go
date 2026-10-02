package sched

import "time"

type Reminder struct {
	Name string
	At   time.Time
}

func Due(rs []Reminder, now time.Time) []Reminder {
	var due []Reminder
	for _, r := range rs {
		if !r.At.After(now) {
			due = append(due, r)
		}
	}
	return due
}
