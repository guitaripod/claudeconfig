# X For You — synced production defaults
synced: 2026-10-08 15:27 UTC from xai-org/x-algorithm@main

| param | type | default | source |
|---|---|---|---|
| `ColdStartBetaAlpha0` | f64 | 0.75 | `home-mixer/params/param.rs` |
| `ColdStartBetaBeta0` | f64 | 49.25 | `home-mixer/params/param.rs` |
| `ColdStartFollowerCap` | i64 | 50000 | `home-mixer/params/param.rs` |
| `ColdStartImpressionScale` | f64 | 1.0 | `home-mixer/params/param.rs` |
| `ColdStartImpressionThreshold` | u32 | 200 | `home-mixer/params/param.rs` |
| `ColdStartMaxPostAgeSecs` | u64 | 7200 | `home-mixer/params/param.rs` |
| `ColdStartSlotMax` | u32 | 16 | `home-mixer/params/param.rs` |
| `ColdStartSlotMin` | u32 | 15 | `home-mixer/params/param.rs` |
| `ColdStartTsTopK` | u32 | 2 | `home-mixer/params/param.rs` |
| `EnableColdStartThompsonSampling` | bool | true | `home-mixer/params/param.rs` |
| `EnablePhoenixOonReplies` | bool | false | `home-mixer/params/param.rs` |
| `EnablePopularPostsSource` | bool | true | `home-mixer/params/param.rs` |
| `EnableViewerColdStart` | bool | true | `home-mixer/params/param.rs` |
| `LowImpressionsMaxPositionRatio` | f64 | 0.97 | `home-mixer/params/param.rs` |
| `PopularPostsMaxResults` | u32 | 500 | `home-mixer/params/param.rs` |
| `SimclustersMaxCandidateAgeHours` | i32 | 48 | `home-mixer/params/param.rs` |
| `AuthorDiversityDecay` | f64 | 0.5 | `vm-ranker/params.rs` |
| `AuthorDiversityFloor` | f64 | 0.25 | `vm-ranker/params.rs` |
| `BidirectionalFollowDwellWeightBoost` | f64 | 0.0 | `vm-ranker/params.rs` |
| `BidirectionalFollowReplyWeightBoost` | f64 | 15.0 | `vm-ranker/params.rs` |
| `BlockAuthorWeight` | f64 | -31.2 | `vm-ranker/params.rs` |
| `ClickWeight` | f64 | 0.3 | `vm-ranker/params.rs` |
| `ContClickDwellTimeWeight` | f64 | 0.4 | `vm-ranker/params.rs` |
| `ContDwellTimeWeight` | f64 | 0.004 | `vm-ranker/params.rs` |
| `DppEnabled` | bool | true | `vm-ranker/params.rs` |
| `DppMaxSelectedRank` | u32 | 150 | `vm-ranker/params.rs` |
| `DppTheta` | f64 | 0.65 | `vm-ranker/params.rs` |
| `DwellWeight` | f64 | 0.05 | `vm-ranker/params.rs` |
| `EnableAuthorDiversity` | bool | true | `vm-ranker/params.rs` |
| `EnableOonRescoreForInNetworkRepliesRetweets` | bool | true | `vm-ranker/params.rs` |
| `EnableQuotedVqvDurationCheck` | bool | false | `vm-ranker/params.rs` |
| `FavoriteWeight` | f64 | 0.5 | `vm-ranker/params.rs` |
| `FollowAuthorWeight` | f64 | 4.0 | `vm-ranker/params.rs` |
| `MinVideoDurationMs` | i32 | 10_000 | `vm-ranker/params.rs` |
| `MuteAuthorWeight` | f64 | -58.8 | `vm-ranker/params.rs` |
| `NewUserOonWeightFactor` | f64 | 0.00001 | `vm-ranker/params.rs` |
| `NotDwelledWeight` | f64 | -0.02 | `vm-ranker/params.rs` |
| `NotInterestedWeight` | f64 | -47.52 | `vm-ranker/params.rs` |
| `OonWeightFactor` | f64 | 0.75 | `vm-ranker/params.rs` |
| `OpenLinkWeight` | f64 | 0.2 | `vm-ranker/params.rs` |
| `PhotoExpandWeight` | f64 | 0.05 | `vm-ranker/params.rs` |
| `PostUnexploredWeight` | f64 | 0.02 | `vm-ranker/params.rs` |
| `ProfileClickWeight` | f64 | 0.0 | `vm-ranker/params.rs` |
| `ProfileVisitSecsWeight` | f64 | 0.0 | `vm-ranker/params.rs` |
| `QuoteWeight` | f64 | 5.0 | `vm-ranker/params.rs` |
| `QuotedClickWeight` | f64 | 0.05 | `vm-ranker/params.rs` |
| `QuotedVqvWeight` | f64 | 0.0 | `vm-ranker/params.rs` |
| `ReplyWeight` | f64 | 5.0 | `vm-ranker/params.rs` |
| `ReportWeight` | f64 | -234.0 | `vm-ranker/params.rs` |
| `RetweetWeight` | f64 | 1.0 | `vm-ranker/params.rs` |
| `ShareViaCopyLinkWeight` | f64 | 20.0 | `vm-ranker/params.rs` |
| `ShareViaDmWeight` | f64 | 5.0 | `vm-ranker/params.rs` |
| `ShareWeight` | f64 | 2.0 | `vm-ranker/params.rs` |
| `TopicOonWeightFactor` | f64 | 0.5 | `vm-ranker/params.rs` |
| `UserVideoContinuationWeight` | f64 | 0.0 | `vm-ranker/params.rs` |
| `VideoContinuationWeight` | f64 | 0.0 | `vm-ranker/params.rs` |
| `VideoOpenWeight` | f64 | 0.07 | `vm-ranker/params.rs` |
| `VqvWeight` | f64 | 0.0 | `vm-ranker/params.rs` |
| `WeightPerturbationSigma` | f64 | 0.0 | `vm-ranker/params.rs` |

Other fixed facts (re-verify in-repo before quoting):
- MAX_POST_AGE = 48h (`home-mixer/params/config.rs`)
- Popular-posts pool: 24h window, 8h view half-life, 5 per author, 500 budget, refreshed hourly, seeded from top 0.005% of active posters by followers (`home-mixer/util/popular_posts.rs`, `util/popular_authors.rs`)
- User-cred: score = clamp(165.2 + 7.07·ln(mass), 0, 100); >= 50 or is_high skips most enforcement (`user-cred-v2/UserCredV2.scala`)
- PTOS high-fav screen threshold: 128 favs (`grox/flows/ptos/constants.py`)
