for (int c1 = -1024; c1 <= 0; c1 += 32)
  for (int c2 = max(-((niter - c1) % 32) + niter - c1 - 32, -((niter - 1) % 32) + niter - 1); c2 <= min(niter + 1022, niter - c1 - 1); c2 += 32)
    for (int c5 = max(max(niter - c1 - c2 - 32, -c1 - 1023), 0); c5 <= min(min(-c1, niter - c1 - c2 - 1), 31); c5 += 1)
      S_4(niter - 1, -c1 - c5);
