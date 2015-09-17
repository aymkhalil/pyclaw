import shocksine
import cProfile, pstats, StringIO

pr = cProfile.Profile()
pr.enable()

#Start
shocksine.run()
#End

pr.disable()
s = StringIO.StringIO()
sortby = 'cumulative'
#sortby = 'tottime'
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()

#from IPython import embed
#embed()

#f = open('profile.txt', 'w')
#f.write(s.getvalue())
#s.close()

print '\n'.join(s.getvalue().splitlines()[0:50])
#print s.getvalue()
