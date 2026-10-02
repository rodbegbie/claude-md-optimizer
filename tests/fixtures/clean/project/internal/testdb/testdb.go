package testdb

import (
	"fmt"
	"testing"
)

func NewSchema(t *testing.T) string {
	t.Helper()
	return fmt.Sprintf("test_%s", t.Name())
}
