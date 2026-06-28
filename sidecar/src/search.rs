use chrono::{DateTime, Duration, Utc};
use glob::glob;
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader};
use std::fs::File;

#[derive(Deserialize)]
pub struct SearchRequest {
    pub keywords: Vec<String>,
    pub log_paths: Vec<String>,
    pub time_window_minutes: Option<u64>,
    pub max_lines: Option<usize>,
}

#[derive(Serialize)]
pub struct MatchedLine {
    pub line_number: usize,
    pub content: String,
}

#[derive(Serialize)]
pub struct FileResult {
    pub path: String,
    pub matched_lines: Vec<MatchedLine>,
    pub total_matched: usize,
    pub error: Option<String>,
}

#[derive(Serialize)]
pub struct SearchResponse {
    pub results: Vec<FileResult>,
    pub total_files_searched: usize,
}

pub fn search_logs(req: SearchRequest) -> SearchResponse {
    let max_lines = req.max_lines.unwrap_or(50);
    let cutoff: Option<DateTime<Utc>> = req.time_window_minutes.map(|mins| {
        Utc::now() - Duration::minutes(mins as i64)
    });

    let mut results = Vec::new();
    let mut total_files = 0;

    for pattern in &req.log_paths {
        let expanded = match glob(pattern) {
            Ok(paths) => paths,
            Err(e) => {
                results.push(FileResult {
                    path: pattern.clone(),
                    matched_lines: vec![],
                    total_matched: 0,
                    error: Some(format!("Invalid glob pattern: {e}")),
                });
                continue;
            }
        };

        for entry in expanded {
            let path = match entry {
                Ok(p) => p,
                Err(e) => {
                    results.push(FileResult {
                        path: pattern.clone(),
                        matched_lines: vec![],
                        total_matched: 0,
                        error: Some(format!("Glob error: {e}")),
                    });
                    continue;
                }
            };

            if !path.is_file() {
                continue;
            }

            total_files += 1;
            let path_str = path.to_string_lossy().to_string();

            let file = match File::open(&path) {
                Ok(f) => f,
                Err(e) => {
                    results.push(FileResult {
                        path: path_str,
                        matched_lines: vec![],
                        total_matched: 0,
                        error: Some(format!("Cannot open file: {e}")),
                    });
                    continue;
                }
            };

            let reader = BufReader::new(file);
            let mut matched_lines = Vec::new();
            let mut total_matched = 0;
            let keywords_lower: Vec<String> = req.keywords.iter().map(|k| k.to_lowercase()).collect();

            for (idx, line_result) in reader.lines().enumerate() {
                let line = match line_result {
                    Ok(l) => l,
                    Err(_) => continue,
                };

                if let Some(cutoff_time) = cutoff {
                    if !line_is_recent(&line, cutoff_time) {
                        continue;
                    }
                }

                let line_lower = line.to_lowercase();
                let matches = keywords_lower.iter().any(|kw| line_lower.contains(kw.as_str()));

                if matches {
                    total_matched += 1;
                    if matched_lines.len() < max_lines {
                        matched_lines.push(MatchedLine {
                            line_number: idx + 1,
                            content: line,
                        });
                    }
                }
            }

            results.push(FileResult {
                path: path_str,
                matched_lines,
                total_matched,
                error: None,
            });
        }
    }

    SearchResponse { results, total_files_searched: total_files }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn make_req(keywords: &[&str], paths: &[String]) -> SearchRequest {
        SearchRequest {
            keywords: keywords.iter().map(|s| s.to_string()).collect(),
            log_paths: paths.to_vec(),
            time_window_minutes: None,
            max_lines: None,
        }
    }

    fn write_log(lines: &[&str]) -> NamedTempFile {
        let mut f = NamedTempFile::new().unwrap();
        for line in lines {
            writeln!(f, "{line}").unwrap();
        }
        f
    }

    #[test]
    fn keyword_match_case_insensitive() {
        let f = write_log(&["INFO Curve building completed", "DEBUG unrelated line"]);
        let path = f.path().to_string_lossy().to_string();
        let resp = search_logs(make_req(&["CURVE"], &[path]));
        assert_eq!(resp.total_files_searched, 1);
        let result = &resp.results[0];
        assert_eq!(result.total_matched, 1);
        assert_eq!(result.matched_lines[0].line_number, 1);
        assert!(result.matched_lines[0].content.contains("Curve building"));
    }

    #[test]
    fn any_keyword_matches() {
        let f = write_log(&["error in module A", "warning threshold exceeded", "all good"]);
        let path = f.path().to_string_lossy().to_string();
        let resp = search_logs(make_req(&["error", "warning"], &[path]));
        assert_eq!(resp.results[0].total_matched, 2);
    }

    #[test]
    fn no_match_returns_empty() {
        let f = write_log(&["INFO everything fine", "DEBUG startup complete"]);
        let path = f.path().to_string_lossy().to_string();
        let resp = search_logs(make_req(&["fatal"], &[path]));
        assert_eq!(resp.results[0].total_matched, 0);
        assert!(resp.results[0].matched_lines.is_empty());
    }

    #[test]
    fn max_lines_caps_returned_lines_but_not_total_matched() {
        let lines: Vec<String> = (0..10).map(|i| format!("error event {i}")).collect();
        let line_refs: Vec<&str> = lines.iter().map(|s| s.as_str()).collect();
        let f = write_log(&line_refs);
        let path = f.path().to_string_lossy().to_string();
        let mut req = make_req(&["error"], &[path]);
        req.max_lines = Some(3);
        let resp = search_logs(req);
        assert_eq!(resp.results[0].total_matched, 10);
        assert_eq!(resp.results[0].matched_lines.len(), 3);
    }

    #[test]
    fn invalid_glob_returns_error_result() {
        let resp = search_logs(make_req(&["error"], &["[invalid".to_string()]));
        assert_eq!(resp.total_files_searched, 0);
        assert!(resp.results[0].error.is_some());
    }

    #[test]
    fn nonexistent_glob_returns_no_results() {
        let resp = search_logs(make_req(&["error"], &["/tmp/logsight_nonexistent_xyz_*.log".to_string()]));
        assert_eq!(resp.total_files_searched, 0);
        assert!(resp.results.is_empty());
    }

    #[test]
    fn line_numbers_are_one_based() {
        let f = write_log(&["skip", "match this", "skip"]);
        let path = f.path().to_string_lossy().to_string();
        let resp = search_logs(make_req(&["match"], &[path]));
        assert_eq!(resp.results[0].matched_lines[0].line_number, 2);
    }

    #[test]
    fn multiple_files_via_glob() {
        let dir = tempfile::tempdir().unwrap();
        for i in 0..3 {
            let p = dir.path().join(format!("app{i}.log"));
            std::fs::write(&p, "error occurred\n").unwrap();
        }
        let pattern = dir.path().join("*.log").to_string_lossy().to_string();
        let resp = search_logs(make_req(&["error"], &[pattern]));
        assert_eq!(resp.total_files_searched, 3);
        assert_eq!(resp.results.len(), 3);
    }

    #[test]
    fn time_window_excludes_old_lines() {
        let old = "2000-01-01 00:00:00 ERROR ancient failure";
        let recent = format!(
            "{} ERROR recent failure",
            chrono::Utc::now().format("%Y-%m-%d %H:%M:%S")
        );
        let f = write_log(&[old, recent.as_str()]);
        let path = f.path().to_string_lossy().to_string();
        let mut req = make_req(&["error"], &[path]);
        req.time_window_minutes = Some(60);
        let resp = search_logs(req);
        assert_eq!(resp.results[0].total_matched, 1);
        assert!(resp.results[0].matched_lines[0].content.contains("recent"));
    }

    #[test]
    fn line_is_recent_unparseable_timestamp_included() {
        let cutoff = Utc::now();
        assert!(line_is_recent("no timestamp here just text", cutoff));
    }

    #[test]
    fn line_is_recent_old_iso8601_excluded() {
        let cutoff = Utc::now();
        assert!(!line_is_recent("2000-01-01T00:00:00Z ERROR old", cutoff));
    }

    #[test]
    fn line_is_recent_future_iso8601_included() {
        let cutoff = Utc::now() - Duration::hours(1);
        let ts = Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
        let line = format!("{ts} INFO something");
        assert!(line_is_recent(&line, cutoff));
    }
}

fn line_is_recent(line: &str, cutoff: DateTime<Utc>) -> bool {
    // Try to parse common timestamp formats from the start of the line
    let candidates = [
        // ISO 8601 / RFC3339 with offset e.g. "2024-01-15T14:23:01+00:00"
        &line[..std::cmp::min(25, line.len())],
        // RFC3339 with Z suffix e.g. "2024-01-15T14:23:01Z"
        &line[..std::cmp::min(20, line.len())],
        // Naive datetime e.g. "2024-01-15 14:23:01"
        &line[..std::cmp::min(19, line.len())],
    ];

    for candidate in candidates {
        if let Ok(dt) = DateTime::parse_from_rfc3339(candidate) {
            return dt.with_timezone(&Utc) >= cutoff;
        }
        // Try "YYYY-MM-DD HH:MM:SS" format
        if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(candidate, "%Y-%m-%d %H:%M:%S") {
            let utc: DateTime<Utc> = DateTime::from_naive_utc_and_offset(dt, Utc);
            return utc >= cutoff;
        }
    }

    // If we can't parse a timestamp, include the line
    true
}
