#ifndef ISL_SCHEDLUE_PRIVATE_H
#define ISL_SCHEDLUE_PRIVATE_H

#include <isl/schedule.h>

/* The schedule for an individual domain, plus information about the bands.
 * In particular, we keep track of the number of bands and for each
 * band, the starting position of the next band.  The first band starts at
 * position 0.
 */
struct isl_schedule_node {
	isl_map *sched;
	int	 n_band;
	int	*band_end;
	int	*band_id;
};

/* Information about the computed schedule.
 * n is the number of nodes/domains/statements.
 * n_band is the maximal number of bands.
 * n_total_row is the number of coordinates of the schedule.
 * dim contains a description of the parameters.
 */
struct isl_schedule {
	int ref;

	int n;
	int n_band;
	int n_total_row;
	isl_dim *dim;

	struct isl_schedule_node node[1];
};

#endif