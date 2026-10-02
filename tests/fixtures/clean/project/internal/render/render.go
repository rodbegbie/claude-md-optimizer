package render

import "time"

func Local(t time.Time, zone *time.Location) string {
	return t.In(zone).Format(time.Kitchen)
}
